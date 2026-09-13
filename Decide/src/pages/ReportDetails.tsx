import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Button,
  CircularProgress,
  Alert,
  List,
  ListItem,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Switch,
  FormControlLabel,
  Grid,
  Chip,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useNavigate, useParams } from 'react-router-dom';
import { RedditAudienceReport, Report, getReportById } from '../services/reportFirebaseService';
import { parseStructuredTextWithTables } from 'utils';
import { doc, updateDoc } from 'firebase/firestore';
import { db, auth } from '../firebase';

const PageContainer = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.background.default,
  minHeight: '100vh',
  padding: theme.spacing(3),
}));

const DetailsPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4),
  marginTop: theme.spacing(3),
}));

const ReportDetails: React.FC = () => {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isPublic, setIsPublic] = useState(false);
  const [isAuthor, setIsAuthor] = useState(false);
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();

  useEffect(() => {
    fetchReportDetails();
  }, [id]);

  const fetchReportDetails = async () => {
    if (!id) {
      setError('Report ID is missing');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const reportData = await getReportById(id);

      if (!reportData) {
        setError('Report not found');
      } else {
        setReport(reportData);
        setIsPublic(reportData.public || false);
        // Check if current user is the author
        const currentUser = auth.currentUser;
        setIsAuthor(currentUser?.uid === reportData.authorId);
      }
    } catch (error) {
      setError('Error loading report details');
      console.error('Error fetching report details:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePublicToggle = async (event: React.ChangeEvent<HTMLInputElement>) => {
    if (!id) return;

    const newPublicState = event.target.checked;
    try {
      const reportRef = doc(db, 'reports', id);
      await updateDoc(reportRef, {
        public: newPublicState
      });
      setIsPublic(newPublicState);
    } catch (error) {
      console.error('Error updating report visibility:', error);
      // Revert the switch state if update fails
      setIsPublic(!newPublicState);
    }
  };

  const renderBackButton = () => (
    <Button
      startIcon={<ArrowBackIcon />}
      onClick={() => navigate('/reports')}
      variant="outlined"
      sx={{ mb: 2 }}
    >
      Back to Reports
    </Button>
  );

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !report) {
    return (
      <PageContainer>
        {renderBackButton()}
        <Alert severity="error" sx={{ mt: 2 }}>
          {error || 'Report not found'}
        </Alert>
      </PageContainer>
    );
  }


  const getFileName = () => {
    const type = report.type;
    const date = new Date(report.createdAt);

    // Include title and format date to YYYYMMDD
    const title = report.inputData.title;

    let typeFileName = "";

    if (type === "marketing-strategy") {
      typeFileName = "marketing_strategy";
    } else if (type === "early-adapters") {
      typeFileName = "early_adopter_strategy";
    } else if (type === "go-to-market") {
      typeFileName = "gtm_strategy";
    }

    // Format date: YYYYMMDD (only date part)
    const iso = date.toISOString(); // e.g. "2025-05-08T15:43:12.345Z"
    const datePart = iso.slice(0, 10).replace(/-/g, ''); // YYYYMMDD

    // Construct the filename
    const filename = `${typeFileName}_${title}_${datePart}.pdf`;
    return filename;
  };


  console.log(report);

  const formatPersonalityText = (text: string) => {
    // Split the text by ** and map through parts
    const parts = text.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        // Remove ** and make text bold
        const boldText = part.slice(2, -2);
        return <strong key={index}>{boldText}</strong>;
      }
      return part;
    });
  };

  //08.05.2025 -> check if there is public interests - and expand in the way most convenient and sensible
  return (
    <PageContainer>
      {renderBackButton()}

      {report.type === 'reddit-audience' ? (
        <DetailsPaper>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
            <Box>
              <Typography variant="h4" color="primary" gutterBottom>
                {report.inputData.title}
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Typography variant="subtitle1" color="text.secondary">Target Community:</Typography>
                <a
                  href={`https://www.reddit.com/r/${report.inputData.community}/`}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ textDecoration: 'none' }}
                >
                  <Typography variant="subtitle1" color="secondary" sx={{ '&:hover': { textDecoration: 'underline' } }}>
                    r/{report.inputData.community}
                  </Typography>
                </a>
              </Box>
            </Box>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 1 }}>
              {isAuthor && (
                <FormControlLabel
                  control={
                    <Switch
                      checked={isPublic}
                      onChange={handlePublicToggle}
                      color="primary"
                    />
                  }
                  label="Make Public"
                />
              )}
              <Typography color="text.secondary" variant="subtitle1">
                {report.data.length} people portraits
              </Typography>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {report.data.map((item: RedditAudienceReport, index: number) => (
              <Paper key={index} elevation={2} sx={{ p: 3 }}>
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" color="primary" gutterBottom>
                    User: {item.username}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Analysis Date: {new Date(item.analysis_date).toLocaleDateString()}
                  </Typography>
                </Box>

                <Grid container spacing={3}>
                  {/* Sentiment Analysis */}
                  <Grid item xs={12} md={4}>
                    <Paper elevation={1} sx={{ p: 2, bgcolor: 'background.default' }}>
                      <Typography variant="subtitle1" gutterBottom>
                        Sentiment Analysis
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                        <Chip
                          label={`Positive: ${item.emotions.positive}`}
                          color="success"
                          size="small"
                        />
                        <Chip
                          label={`Negative: ${item.emotions.negative}`}
                          color="error"
                          size="small"
                        />
                        <Chip
                          label={`Neutral: ${item.emotions.neutral}`}
                          color="default"
                          size="small"
                        />
                      </Box>
                      <Typography variant="body2">
                        Overall Sentiment: <strong>{item.sentiment}</strong>
                      </Typography>
                      <Typography variant="subtitle1" gutterBottom>
                        Key Topics
                      </Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        {item.topics.map((topic, idx) => (
                          <Chip
                            key={idx}
                            label={topic}
                            color="primary"
                            variant="outlined"
                            size="small"
                          />
                        ))}
                      </Box>
                      <Typography variant="subtitle1" gutterBottom>
                        Top Upvoted Comments
                      </Typography>
                      <List dense>
                        {item.top_upvoted_comments.map((comment, idx) => (
                          <ListItem key={idx} sx={{ display: 'block', mb: 1 }}>
                            <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                              "{comment}"
                            </Typography>
                          </ListItem>
                        ))}
                      </List>
                    </Paper>
                  </Grid>

                  <Grid item xs={12} md={8}>
                    <Paper elevation={1} sx={{ p: 2, bgcolor: 'background.default' }}>
                      <Typography variant="subtitle1" gutterBottom>
                        Personality Analysis
                      </Typography>
                      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
                        {formatPersonalityText(item.personality)}
                      </Typography>
                    </Paper>
                  </Grid>
                </Grid>
              </Paper>
            ))}
          </Box>
        </DetailsPaper>
      ) : (
        <>
          <DetailsPaper>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="h4" color="primary">
                {report.data.title}
              </Typography>

              <a
                href={`https://storage.googleapis.com/authentic_scope_docs/${getFileName()}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Typography variant="h6" color="primary">
                  Download file
                </Typography>
              </a>

              {isAuthor && (
                <FormControlLabel
                  control={
                    <Switch
                      checked={isPublic}
                      onChange={handlePublicToggle}
                      color="primary"
                    />
                  }
                  label="Make Public"
                />
              )}
            </Box>
            {report?.inputData && (
              <Box sx={{ mb: 4 }}>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                  User data:
                </Typography>
                <List dense disablePadding>
                  {Object.entries(report.inputData).map(([key, value]) => (
                    <ListItem key={key} sx={{ display: 'list-item', pl: 2 }}>
                      <Typography variant="body2">
                        <strong>{key}:</strong> {String(value)}
                      </Typography>
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}

            <Box sx={{ mt: 6 }}>
              <Typography variant="h6" color="text.secondary" gutterBottom>
                Report Type
              </Typography>
              <Typography variant="body1" gutterBottom>
                {report?.type?.split('-').map(word =>
                  word.charAt(0).toUpperCase() + word.slice(1)
                ).join(' ')}
              </Typography>

              <Typography variant="h6" color="text.secondary" gutterBottom sx={{ mt: 3 }}>
                Created At
              </Typography>
              <Typography variant="body1">
                {new Intl.DateTimeFormat('en-US', {
                  dateStyle: 'full',
                  timeStyle: 'long',
                }).format(report?.createdAt)}
              </Typography>
            </Box>
            <hr />



            <Box sx={{ mt: 4 }}>
              {Object.entries(report.data)
                .filter(([key]) => key !== 'title')
                .map(([key, value]) => {
                  const parsed = parseStructuredTextWithTables(value as string);

                  return (
                    <Box key={key} sx={{ mb: 4 }}>
                      <Typography variant="h3" color="text.secondary" gutterBottom>
                        {key
                          .split('_')
                          .map(word => word.charAt(0).toUpperCase() + word.slice(1))
                          .join(' ')}
                      </Typography>

                      {/* Render Sections */}
                      {parsed.sections.length > 0 && parsed.sections.map((section, idx) => (
                        <Box key={idx} sx={{ mb: 2 }}>
                          <Typography variant="h5" fontWeight="bold" gutterBottom>
                            {section.header}
                          </Typography>
                          <List dense disablePadding>
                            {section.subpoints.map((sp, i) => (
                              <ListItem key={i} sx={{ display: 'list-item', pl: 2 }}>
                                <Typography variant="body2">
                                  <strong>{sp.title}:</strong> {sp.desc}
                                </Typography>
                              </ListItem>
                            ))}
                          </List>
                        </Box>
                      ))}

                      {/* Render Tables */}
                      {parsed.tables.length > 0 && parsed.tables.map((table, idx) => (
                        <Box key={`table-${idx}`} sx={{ mb: 2 }}>
                          <Typography variant="h5" fontWeight="bold" gutterBottom>
                            {table.header || 'Table'} {/* Display table header */}
                          </Typography>
                          <Table sx={{ width: '100%' }}>
                            <TableHead>
                              <TableRow>
                                {Object.keys(table.rows[0] || {}).map((header, i) => (
                                  <TableCell key={i} sx={{ fontWeight: 'bold' }}>
                                    {header}
                                  </TableCell>
                                ))}
                              </TableRow>
                            </TableHead>
                            <TableBody>
                              {table.rows.map((row, rowIndex) => (
                                <TableRow key={rowIndex}>
                                  {Object.values(row).map((cell, cellIndex) => (
                                    //@ts-ignore
                                    <TableCell key={cellIndex}>{cell}</TableCell>
                                  ))}
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </Box>
                      ))}

                      {/* Fallback for raw text */}
                      {!parsed.sections.length && !parsed.tables.length && (
                        <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                          {value as string}
                        </Typography>
                      )}
                    </Box>
                  );
                })}
            </Box>
          </DetailsPaper>
        </>
      )}
    </PageContainer>
  );
};

export default ReportDetails;