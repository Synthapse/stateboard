import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemText,
  useTheme,
  useMediaQuery,
  Chip,
  Button,
  Snackbar,
  Alert,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import DashboardIcon from '@mui/icons-material/Dashboard';
import PeopleIcon from '@mui/icons-material/People';
import PsychologyIcon from '@mui/icons-material/Psychology';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import VideocamIcon from '@mui/icons-material/Videocam';
import AnalyticsIcon from '@mui/icons-material/Analytics';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';
import CampaignIcon from '@mui/icons-material/Campaign';
import CreditCardIcon from '@mui/icons-material/CreditCard';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import { getAllFeatureVotes, incrementFeatureVote, FeatureVoteData } from '../services/featureService';

const PageHeader = styled(Box)(({ theme }) => ({
  background: theme.palette.background.paper,
  padding: theme.spacing(10, 0, 8),
  marginBottom: theme.spacing(4),
  textAlign: 'center',
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const FeatureCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[4],
  },
}));

const StyledFeatureIcon = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(1),
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginRight: theme.spacing(1.5),
  verticalAlign: 'middle',
}));

type FeatureStatus = 'done' | 'todo' | 'partially done';

interface Feature {
  id: string;
  title: string;
  icon: JSX.Element;
  description: string;
  items: string[];
  status: FeatureStatus;
  votes: number;
  voterIPs?: string[];
  hasVoted?: boolean;
}

const initialFeaturesData: Omit<Feature, 'votes' | 'voterIPs' | 'hasVoted'>[] = [
  {
    id: 'projects-dashboard',
    title: 'Projects Dashboard',
    icon: <DashboardIcon />,
    description: 'Project Management',
    items: [
      'Create, track, and manage marketing projects',
      'Assign goals, deadlines, and team members',
      'Reporting Tools',
      'Generate reports per project (performance, audience impact, engagement metrics)',
      'Visual dashboards (KPIs, ROI)',
    ],
    status: 'todo',
  },
  {
    id: 'audience-intelligence',
    title: 'Audience Intelligence',
    icon: <PeopleIcon />,
    description: 'AI-Powered Audience Research',
    items: [
      'Behavior-based segmentation (via browsing, interests, keywords)',
      'Audience persona generation',
      'Psychological Profiling',
      'Individual-level profiling',
      'Group-level/network psychology synthesis',
      'Correlation engine (shared traits, behavior models)',
    ],
    status: 'partially done',
  },
  {
    id: 'ai-agents',
    title: 'AI Agents',
    icon: <PsychologyIcon />,
    description: 'Autonomous Tools',
    items: [
      'Marketing Strategist Agent',
      'Suggest campaigns, messages, and target segments',
      'Data Analyst Agent',
      'Interprets audience data, social trends, and funnel performance',
    ],
    status: 'partially done',
  },
  {
    id: 'audience-generation',
    title: 'Audience Generation',
    icon: <AutoAwesomeIcon />,
    description: 'Automation Tools',
    items: [
      'Reddit Agent',
      'Scrapes subreddits for personality insights',
      'Clusters posts/comments into audience profiles',
      'Twitter Agent',
      'Tracks hashtags and sentiment',
      'Identifies micro-influencers and communities',
    ],
    status: 'partially done',
  },
  {
    id: 'video-session-analyzer',
    title: 'Video Session Analyzer',
    icon: <VideocamIcon />,
    description: 'Video Analysis Tool',
    items: [
      'Auto-tag emotional states, engagement peaks',
      'Extract highlights, segment viewer feedback',
      'Integration with open-source AI video analyzers',
    ],
    status: 'todo',
  },
  {
    id: 'customer-analytics',
    title: 'Customer Analytics',
    icon: <AnalyticsIcon />,
    description: 'Analytics Suite',
    items: [
      'Behavior Tracking',
      'Integrate tools like Hotjar for session data',
      'Funnel behavior, bounce points, and UX issues',
      'Segment Integration',
      'Sync user profiles from Segment.com',
      'Track across devices and platforms',
    ],
    status: 'todo',
  },
  {
    id: 'early-adopters-program',
    title: 'Early Adopters Program',
    icon: <RocketLaunchIcon />,
    description: 'Toolkit',
    items: [
      'Landing Page Builder',
      'Quick deployment for MVP/test interest',
      'Outreach Assistant',
      'Generate personalized outreach DMs',
      'Suggest value-offers (e.g., free trial, mentorship)',
      'User Onboarding & Feedback',
      'Welcome emails + guided tour',
      'In-app surveys, NPS tracking',
      'Perks: credits, early access, social recognition',
    ],
    status: 'done',
  },
  {
    id: 'marketing-strategy-hub',
    title: 'Marketing Strategy Hub',
    icon: <CampaignIcon />,
    description: 'Strategy Tools',
    items: [
      'AI-Generated Strategies',
      'Campaign blueprints based on audience data',
      'Multichannel recommendations (email, social, community)',
      'Competitive Analysis',
      'Benchmark features vs. Exolyt, Aha!, HumanBehavior.co',
      'Integration Center',
      'APIs for HotJar, Segment, Notion, custom CRM',
    ],
    status: 'todo',
  },
  {
    id: 'stripe-integration',
    title: 'Stripe Integration',
    icon: <CreditCardIcon />,
    description: 'Payment Processing & Subscriptions',
    items: [
      'Secure payment gateway for services',
      'Manage subscription plans and billing',
    ],
    status: 'todo',
  },
];


const Features: React.FC = () => {
  const theme = useTheme();
  const [features, setFeatures] = useState<Feature[]>([]);
  const [loading, setLoading] = useState(true);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [snackbarSeverity, setSnackbarSeverity] = useState<'success' | 'error' | 'info'>('info');
  const [userIP, setUserIP] = useState('');

  useEffect(() => {
    const fetchVotes = async () => {
      setLoading(true);
      try {


        fetch('https://api.ipify.org?format=json')
          .then(response => response.json())
          .then(async data => {
            const userIP = data.ip;
            console.log('User IP:', userIP);
            setUserIP(userIP);
            const votesMap = await getAllFeatureVotes();

            const allVotersIPs = Object.values(votesMap).flatMap(vote => vote.voterIPs || []);
            console.log('All voters IPs:', allVotersIPs);
            console.log('User IP:', userIP);
    
            if (allVotersIPs.includes(userIP)) {
              setSnackbarMessage('You have already voted.');
              setSnackbarSeverity('error');
              setSnackbarOpen(true);
            }
    
            const populatedFeatures = initialFeaturesData.map(f => {
              const voteData = votesMap[f.id];
              return {
                ...f,
                votes: voteData?.votes || 0,
                voterIPs: voteData?.voterIPs || [],
                hasVoted: allVotersIPs.includes(userIP) ? true : voteData?.voterIPs?.includes(userIP) || false,
              };
            });
            setFeatures(populatedFeatures);
          })
          .catch(error => {
            console.error('Error fetching IP:', error);
          });

      } catch (error) {
        console.error("Error fetching feature votes:", error);
        setSnackbarMessage('Could not load feature votes.');
        setSnackbarSeverity('error');
        setSnackbarOpen(true);
        setFeatures(initialFeaturesData.map(f => ({ ...f, votes: 0, voterIPs: [], hasVoted: false })));
      }
      setLoading(false);
    };
    fetchVotes();
  }, []);

  const handleVote = async (featureId: string) => {

    setFeatures(prevFeatures => prevFeatures.map(f => f.id === featureId ? { ...f, isVoting: true } : f));

    const result = await incrementFeatureVote(featureId, userIP);

    if (result.success) {
      setSnackbarMessage(result.message || 'Voted successfully!');
      setSnackbarSeverity('success');
      setFeatures(prevFeatures =>
        prevFeatures.map(f =>
          f.id === featureId ? { ...f, votes: result.newVotes !== undefined ? result.newVotes : f.votes + 1, hasVoted: true, isVoting: false } : f
        )
      );
    } else {
      setSnackbarMessage(result.message || 'Failed to vote.');
      setSnackbarSeverity('error');
      setFeatures(prevFeatures => prevFeatures.map(f => f.id === featureId ? { ...f, isVoting: false } : f));
    }
    setSnackbarOpen(true);
  };

  const handleCloseSnackbar = (event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }
    setSnackbarOpen(false);
  };

  const getStatusColor = (status: FeatureStatus): "success" | "warning" | "default" => {
    switch (status) {
      case 'done':
        return 'success';
      case 'partially done':
        return 'warning';
      case 'todo':
      default:
        return 'default';
    }
  };

  const sortedFeatures = [...features].sort((a, b) => {
    const statusOrder: Record<FeatureStatus, number> = {
      'done': 0,
      'partially done': 1,
      'todo': 2,
    };
    const voteDifference = b.votes - a.votes;
    return statusOrder[a.status] - statusOrder[b.status] || voteDifference;
  });

  if (loading) {
    return <Container sx={{ py: 8, textAlign: 'center' }}><Typography>Loading features...</Typography></Container>;
  }

  return (
    <Box sx={{ bgcolor: 'background.default' }}>
      <PageHeader>
        <Container maxWidth="md">
          <Typography
            variant="h2"
            component="h1"
            gutterBottom
            sx={{
              fontWeight: 700,
              color: 'primary.main',
            }}
          >
            Features & Roadmap Voting
          </Typography>
          <Typography
            variant="h5"
            sx={{ color: 'text.secondary', maxWidth: 600, mx: 'auto' }}
          >
            Discover our tools and vote on what we should build next!
          </Typography>
        </Container>
      </PageHeader>

      <Container maxWidth="lg" sx={{ py: 8 }}>
        <Grid container spacing={4}>
          {sortedFeatures.map((feature) => (
            <Grid item xs={12} md={4} key={feature.id}>
              <FeatureCard>
                <CardContent sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Chip
                      label={feature.status.toUpperCase()}
                      color={getStatusColor(feature.status)}
                      size="small"
                      sx={{ fontWeight: 'bold' }}
                    />
                  </Box>

                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
                    <StyledFeatureIcon>{feature.icon}</StyledFeatureIcon>
                    <Typography variant="h5" component="h2" sx={{ flexGrow: 1 }}>
                      {feature.title}
                    </Typography>
                  </Box>

                  <Typography
                    variant="subtitle1"
                    color="text.secondary"
                    gutterBottom
                    sx={{ mb: 2 }}
                  >
                    {feature.description}
                  </Typography>
                  <List dense sx={{ flexGrow: 1 }}>
                    {feature.items.map((item, itemIndex) => (
                      <ListItem key={itemIndex} sx={{ py: 0.5 }}>
                        <ListItemText primary={item} />
                      </ListItem>
                    ))}
                  </List>
                  <Box sx={{ mt: 'auto', pt: 2, display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: `1px solid ${theme.palette.divider}` }}>
                    <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 'medium' }}>
                      Votes: {feature.votes}
                    </Typography>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<ThumbUpIcon />}
                      onClick={() => handleVote(feature.id)}
                      disabled={feature.hasVoted || (feature as any).isVoting}
                    >
                      {feature.hasVoted ? 'Voted' : 'Vote'}
                    </Button>
                  </Box>
                </CardContent>
              </FeatureCard>
            </Grid>
          ))}
        </Grid>
      </Container>
      <Snackbar open={snackbarOpen} autoHideDuration={6000} onClose={handleCloseSnackbar}>
        <Alert onClose={handleCloseSnackbar} severity={snackbarSeverity} sx={{ width: '100%' }}>
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Features; 