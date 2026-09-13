import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Grid,
  Avatar,
  Button,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  IconButton,
  MenuItem,
  Select,
  FormControl,
  InputLabel,
  Chip,
  ListItemSecondaryAction,
} from '@mui/material';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { styled } from '@mui/material/styles';
import StarsIcon from '@mui/icons-material/Stars';
import HistoryIcon from '@mui/icons-material/History';
import SettingsIcon from '@mui/icons-material/Settings';
import DocumentScannerIcon from '@mui/icons-material/DocumentScanner';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import LinkIcon from '@mui/icons-material/Link';
import UnlinkIcon from '@mui/icons-material/LinkOff';
import { Link as RouterLink } from 'react-router-dom';
import { auth, googleProvider } from '../firebase';
import { getUserActivities } from 'services/userActivityService';
import { getUserPoints } from 'services/subscriptionService';
import { getNotionData, getUsers } from 'notion';
import { Project, createProject, getUserProjects, updateProject, deleteProject, addReportToProject, removeReportFromProject } from '../services/projectService';

const PageHeader = styled(Box)(({ theme }) => ({
  background: theme.palette.background.paper,
  padding: theme.spacing(10, 0, 8),
  marginBottom: theme.spacing(4),
  textAlign: 'center',
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const ProfileCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  borderRadius: theme.spacing(2),
  boxShadow: theme.shadows[2],
}));

const PointsDisplay = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  backgroundColor: 'rgba(255, 215, 0, 0.1)',
  borderRadius: theme.spacing(2),
  padding: theme.spacing(2),
  marginBottom: theme.spacing(3),
}));

const PointsIcon = styled(StarsIcon)(({ theme }) => ({
  color: '#FFD700',
  marginRight: theme.spacing(1),
  fontSize: 28,
}));

const ProjectCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  marginBottom: theme.spacing(2),
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-2px)',
    boxShadow: theme.shadows[4],
  },
}));

const ProjectHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  marginBottom: theme.spacing(1),
}));

const ProjectActions = styled(Box)(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(1),
}));

const StatusChip = styled(Chip)(({ theme }) => ({
  marginLeft: theme.spacing(1),
}));

const formatDate = (date: Date) => {
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
};

function renderPageTree(pages: any[], level: number = 0) {
  return (
    <ul style={{ listStyleType: 'none', paddingLeft: 0 }}>
      {pages?.map(page => (
        <li key={page.id} style={{ marginLeft: `${level * 20}px` }}>
          {page.properties?.title?.title?.[0]?.plain_text || 'Untitled'}
          {page.children?.length > 0 && renderPageTree(page.children, level + 1)}
        </li>
      ))}
    </ul>
  );
}

function buildHierarchy(pages: any[]) {
  const idMap: Record<string, any> = {};
  const roots: any[] = [];

  // Step 1: Initialize the map
  pages?.forEach(page => {
    const id = page.id;
    idMap[id] = { ...page, children: [] };
  });

  // Step 2: Link children to parents
  pages?.forEach(page => {
    const parentId = page.parent?.page_id;
    if (parentId && idMap[parentId]) {
      idMap[parentId].children.push(idMap[page.id]);
    } else {
      roots.push(idMap[page.id]); // Root-level page
    }
  });

  return roots;
}

const Profile: React.FC = () => {
  const userId = auth.currentUser?.uid;
  const userName = auth.currentUser?.displayName;
  const userEmail = auth.currentUser?.email;
  const createdAt = auth.currentUser?.metadata.creationTime;
  const avatar = auth.currentUser?.photoURL;

  const [userActivity, setUserActivity] = useState<any[]>([]);
  const [userPoints, setUserPoints] = useState<number>(0);
  const [projects, setProjects] = useState<Project[]>([]);
  const [openProjectDialog, setOpenProjectDialog] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | null>(null);
  const [projectForm, setProjectForm] = useState<{
    title: string;
  }>({
    title: '',
  });

  const [notionData, setNotionData] = useState<any>();
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [openReportDialog, setOpenReportDialog] = useState(false);

  // Mock user data - replace with actual user data from your auth system
  const user = {
    name: userName,
    email: userEmail,
    points: 25,
    avatar: avatar,
    joinDate: createdAt,
  };

  useEffect(() => {
    const fetchUserActivity = async () => {
      const userActivity = await getUserActivities(userId);
      setUserActivity(userActivity);
    };
    fetchUserActivity();
    fetchPoints();
    fetchProjects();

    // // NOTION:
    // const functionUrl = "https://us-central1-voicesense.cloudfunctions.net/getNotionData";

    // // Fetch data from your cloud function
    // fetch(functionUrl)
    //   .then((res) => res.json())
    //   .then((data) => {
    //     console.log(data);
    //     setNotionData(data)
    //   }
    //   )
    //   .catch((err) => console.log(err));

  }, []);

  const fetchPoints = () => {
    getUserPoints(userEmail ?? "").then((points) => {
      setUserPoints(points);
    }).catch((error) => {
      console.error('Error fetching points:', error);
      return 0; // Default to 0 points on error
    });
  }

  const fetchProjects = async () => {
    try {
      const userProjects = await getUserProjects();
      console.log(userProjects);
      setProjects(userProjects);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  };

  const handleOpenProjectDialog = (project?: Project) => {
    if (project) {
      setEditingProject(project);
      setProjectForm({
        title: project.title,
      });
    } else {
      setEditingProject(null);
      setProjectForm({
        title: '',
      });
    }
    setOpenProjectDialog(true);
  };

  const handleCloseProjectDialog = () => {
    setOpenProjectDialog(false);
    setEditingProject(null);
    setProjectForm({
      title: '',
    });
  };

  const handleProjectSubmit = async () => {
    try {
      if (editingProject) {
        await updateProject(editingProject.id!, projectForm);
      } else {
        const newProject = {
          ...projectForm,
          userId: auth.currentUser?.uid || '',
        };
        await createProject(newProject);
      }
      handleCloseProjectDialog();
      fetchProjects();
    } catch (error) {
      console.error('Error saving project:', error);
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (window.confirm('Are you sure you want to delete this project?')) {
      try {
        await deleteProject(projectId);
        fetchProjects();
      } catch (error) {
        console.error('Error deleting project:', error);
      }
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'success';
      case 'completed':
        return 'primary';
      case 'archived':
        return 'default';
      default:
        return 'default';
    }
  };

  const hierarchy = buildHierarchy(notionData?.pages);

  console.log(hierarchy);

  const handleOpenReportDialog = (project: Project) => {
    setSelectedProject(project);
    setOpenReportDialog(true);
  };

  const handleCloseReportDialog = () => {
    setSelectedProject(null);
    setOpenReportDialog(false);
  };

  const handleAddReportToProject = async (reportId: string) => {
    console.log(reportId);
    if (!selectedProject) return;
    try {
      await addReportToProject(selectedProject.id!, reportId);
      fetchProjects();
      handleCloseReportDialog();
    } catch (error) {
      console.error('Error adding report to project:', error);
    }
  };

  const handleRemoveReportFromProject = async (projectId: string, reportId: string) => {
    try {
      await removeReportFromProject(projectId, reportId);
      fetchProjects();
    } catch (error) {
      console.error('Error removing report from project:', error);
    }
  };

  return (
    <Box sx={{ bgcolor: 'background.default' }}>
      <Container maxWidth="lg">
        <Grid container spacing={4}>
          <Grid item xs={12} md={4}>
            <ProfileCard>
              <Box sx={{ textAlign: 'center', mb: 3 }}>
                {avatar &&
                  <Avatar
                    src={avatar}
                    sx={{
                      width: 120,
                      height: 120,
                      margin: '0 auto',
                      mb: 2,
                    }}
                  />
                }
                <Typography variant="h5" gutterBottom>
                  {user.name}
                </Typography>
                <Typography color="text.secondary" gutterBottom>
                  {user.email}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Member since {user.joinDate}
                </Typography>
              </Box>

              <PointsDisplay>
                <PointsIcon />
                <Typography
                  variant="h5"
                  sx={{
                    fontWeight: 600,
                    color: '#B8860B',
                  }}
                >
                  {userPoints} Points
                </Typography>
              </PointsDisplay>

              {/* <Button
                variant="contained"
                color="primary"
                fullWidth
                startIcon={<SettingsIcon />}
                sx={{ mb: 2 }}
              >
                Edit Profile
              </Button> */}
            </ProfileCard>
          </Grid>

          {/* <Grid item xs={12} md={8}>
            <ProfileCard>
              <h2>Notion Integration:</h2>
              {renderPageTree(hierarchy)}
            </ProfileCard>
          </Grid> */}

          <Grid item xs={12} md={8}>
            <ProfileCard>
              <Typography variant="h6" gutterBottom>
                Recent Activity (3)
              </Typography>
              <List>
                {userActivity.slice(0, 3).map((activity) => (
                  <a href={`#/reports/${activity.reportId}`} key={activity.id} style={{ textDecoration: 'none', color: 'inherit' }}>
                    <ListItem key={activity.id}>
                      <ListItemIcon>
                        <DocumentScannerIcon color="primary" />
                      </ListItemIcon>
                      <ListItemText
                        primary={activity.title}
                        secondary={formatDate(activity.createdAt)}
                      />
                    </ListItem>
                  </a>
                ))}
              </List>
            </ProfileCard>
          </Grid>

          <Grid item xs={12}>
            <ProfileCard>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">My Projects</Typography>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<AddIcon />}
                  onClick={() => handleOpenProjectDialog()}
                >
                  New Project
                </Button>
              </Box>
              <Divider sx={{ mb: 2 }} />
              {projects.map((project) => (
                <ProjectCard key={project.id}>
                  <ProjectHeader>
                    <Typography variant="h6">{project.title}</Typography>
                    <ProjectActions>
                      <Button
                        size="small"
                        startIcon={<LinkIcon />}
                        onClick={() => handleOpenReportDialog(project)}
                      >
                        {project.reportIds?.length || 0} Reports
                      </Button>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenProjectDialog(project)}
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteProject(project.id!)}
                      >
                        <DeleteIcon />
                      </IconButton>
                    </ProjectActions>
                  </ProjectHeader>
                  {project.reportIds && project.reportIds.length > 0 && (
                    <List dense>
                      {userActivity
                        .filter(activity => project.reportIds?.includes(activity.reportId))
                        .map(activity => (
                          <ListItem key={activity.id}>
                            <ListItemText
                              primary={activity.title}
                              secondary={formatDate(activity.createdAt)}
                            />
                            <ListItemSecondaryAction>
                              <a target="_blank" href={`#/reports/${activity.reportId}`} key={activity.id} style={{ textDecoration: 'none' }}>
                                <IconButton
                                  edge="end"
                                  size="small"
                                  onClick={() => handleRemoveReportFromProject(project.id!, activity.reportId)}
                                >
                                  <OpenInNewIcon />
                                </IconButton>
                              </a>
                              <IconButton
                                edge="end"
                                size="small"
                                onClick={() => handleRemoveReportFromProject(project.id!, activity.reportId)}
                              >
                                <UnlinkIcon />
                              </IconButton>
                            </ListItemSecondaryAction>
                          </ListItem>
                        ))}
                    </List>
                  )}
                  <Typography variant="caption" color="text.secondary">
                    Created: {formatDate(project.createdAt)}
                  </Typography>
                </ProjectCard>
              ))}
            </ProfileCard>
          </Grid>
        </Grid>
      </Container>

      <Dialog open={openProjectDialog} onClose={handleCloseProjectDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingProject ? 'Edit Project' : 'Create New Project'}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Project Title"
              fullWidth
              value={projectForm.title}
              onChange={(e) => setProjectForm({ ...projectForm, title: e.target.value })}
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseProjectDialog}>Cancel</Button>
          <Button onClick={handleProjectSubmit} variant="contained" color="primary">
            {editingProject ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={openReportDialog} onClose={handleCloseReportDialog} maxWidth="sm" fullWidth>
        <DialogTitle>
          Add Reports to {selectedProject?.title}
        </DialogTitle>
        <DialogContent>
          <List>
            {userActivity
              .filter(activity => !selectedProject?.reportIds?.includes(activity.reportId))
              .map(activity => (
                <ListItem
                  key={activity.id}
                  button
                  onClick={() => handleAddReportToProject(activity.reportId)}
                >
                  <ListItemIcon>
                    <HistoryIcon color="primary" />
                  </ListItemIcon>
                  <ListItemText
                    primary={activity.title}
                    secondary={formatDate(activity.createdAt)}
                  />
                  <ListItemSecondaryAction>
                    <IconButton edge="end" size="small">
                      <LinkIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
          </List>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseReportDialog}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Profile; 