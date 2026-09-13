import React, { useState, useEffect } from 'react';
import {
  Container,
  Typography,
  Box,
  Alert,
  Snackbar,
  CircularProgress,
  Paper,
  Button,
  Chip,
  Grid,
  Card,
  CardContent,
  CardActionArea,
  Tooltip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import ReportForm from '../components/ReportForm';
import { ReportType } from '../types/reports';
import * as reportService from '../services/reportService';
import { collection, addDoc, Timestamp, doc, getDoc, updateDoc, increment } from "firebase/firestore";
import { db, auth } from '../firebase';
import { Link as RouterLink } from 'react-router-dom';
import HistoryIcon from '@mui/icons-material/History';
import StarsIcon from '@mui/icons-material/Stars';
import { addUserActivity } from '../services/userActivityService';
import { getUserPoints, removeUserPoints } from 'services/subscriptionService';

const PageHeader = styled(Box)(({ theme }) => ({
  background: theme.palette.background.paper,
  padding: theme.spacing(2, 0),
  marginBottom: theme.spacing(3),
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const PointCostChip = styled(Chip)(({ theme }) => ({
  marginLeft: theme.spacing(1),
  backgroundColor: 'rgba(255, 215, 0, 0.1)',
  color: '#B8860B',
  fontWeight: 600,
  '& .MuiChip-icon': {
    color: '#FFD700',
  },
}));

// Define point costs for each report type
const REPORT_COSTS = {
  'marketing-strategy': 3,
  'early-adapters': 3,
  'go-to-market': 5,
  'reddit-audience': 15,
};

const ReportTypeCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-4px)',
    boxShadow: theme.shadows[4],
  },
}));

const ReportTypeContent = styled(CardContent)(({ theme }) => ({
  flexGrow: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  textAlign: 'center',
  padding: theme.spacing(3),
}));

const reportTypes = [
  {
    type: 'marketing-strategy' as ReportType,
    title: 'Marketing Strategy',
    description: 'Create a comprehensive digital marketing strategy focusing on content, social media, and targeted campaigns.',
    icon: '📈',
  },
  {
    type: 'early-adapters' as ReportType,
    title: 'Early Adapters',
    description: 'Design and implement an early adopters program to gather feedback and build initial user base.',
    icon: '🚀',
  },
  {
    type: 'go-to-market' as ReportType,
    title: 'Go to Market',
    description: 'Develop a detailed go-to-market strategy for your product launch and market entry.',
    icon: '🎯',
  },
  {
    type: 'reddit-audience' as ReportType,
    title: 'Reddit Audience',
    description: 'Analyze Reddit communities to understand your target audience and market opportunities.',
    icon: '🔍',
  },
];

const Reports: React.FC = () => {

  const userEmail = auth.currentUser?.email;
  const [activeTab, setActiveTab] = useState<ReportType | null>(null);
  const [loading, setLoading] = useState(false);
  const [userPoints, setUserPoints] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(true);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'success',
  });

  useEffect(() => {
    fetchPoints();
  }, []);

  const fetchPoints = () => {

    getUserPoints(userEmail ?? "").then((points) => {
      setUserPoints(points);
      setIsLoading(false); // Set loading to false after fetching points
    }).catch((error) => {
      console.error('Error fetching points:', error);
      return 0; // Default to 0 points on error
    });
  }

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const getReportTitle = (type: ReportType, data: any) => {
    switch (type) {
      case 'marketing-strategy':
        return `Marketing Strategy for ${data?.title || 'Target Audience'}`;
      case 'go-to-market':
        return `Go-to-Market Plan for ${data?.title || 'Product'}`;
      case 'early-adapters':
        return `Early Adopters Analysis for ${data?.title || 'Target Market'}`;
      case 'reddit-audience':
        return `Reddit Audience Analysis for ${data?.title || 'Community'}`;
      default:
        return 'Report';
    }
  };

  const hasEnoughPoints = () => {
    if (!activeTab) return false;
    return userPoints >= REPORT_COSTS[activeTab];
  };

  const handleSubmit = async (data: any) => {
    if (!activeTab) return;
    
    if (!hasEnoughPoints()) {
      setSnackbar({
        open: true,
        message: `Not enough points. You need ${REPORT_COSTS[activeTab]} points to generate this report.`,
        severity: 'warning',
      });
      return;
    }

    setLoading(true);
    try {
      let response;
      switch (activeTab) {
        case 'marketing-strategy':
          response = await reportService.generateMarketingStrategyReport(data);
          break;
        case 'early-adapters':
          response = await reportService.generateEarlyAdaptersReport(data);
          break;
        case 'go-to-market':
          response = await reportService.generateGoToMarketReport(data);
          break;
        case 'reddit-audience':
          response = await reportService.generateRedditAudienceReport(data.community);
          break;
      }

      // Save report to Firebase
      const docRef = await addDoc(collection(db, "reports"), {
        tab: activeTab,
        inputData: data,
        reportText: response.text_content || "",
        createdAt: Timestamp.now(),
        authorId: auth.currentUser?.uid,
        status: 'completed',
        public: false,
      });

      // Add user activity
      const user = auth.currentUser;
      if (user) {
        await addUserActivity({
          userId: user.uid,
          type: activeTab,
          reportId: docRef.id,
          title: getReportTitle(activeTab, data),
          status: 'completed'
        });

        // Deduct points from user's account
        removeUserPoints(userEmail ?? "", REPORT_COSTS[activeTab]).then(() => {
          console.log('Points deducted successfully.');
        }).catch((error) => {
          console.error('Error deducting points:', error);
        });

        // Update local state with new points balance
        setUserPoints(prevPoints => prevPoints - REPORT_COSTS[activeTab]);
      }

      setSnackbar({
        open: true,
        message: 'Report generated successfully!',
        severity: 'success',
      });

    } catch (error) {
      setSnackbar({
        open: true,
        message: 'Failed to generate report. Please try again.',
        severity: 'error',
      });
      console.error('Error generating report:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ bgcolor: 'background.default' }}>
      <PageHeader>
        <Container maxWidth="lg">
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            gap: 2
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography
                variant="body2"
                sx={{ color: 'text.secondary' }}
              >
                Create detailed reports for your marketing strategy, early adapters analysis, and go-to-market planning.
              </Typography>
            </Box>

            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>Points:</Typography>
              <Chip
                icon={<StarsIcon />}
                label={isLoading ? "Loading..." : userPoints}
                size="small"
                sx={{
                  backgroundColor: 'rgba(255, 215, 0, 0.1)',
                  color: '#B8860B',
                  fontWeight: 600,
                  '& .MuiChip-icon': {
                    color: '#FFD700',
                  },
                }}
              />
              <Button
                component={RouterLink}
                to="/pricing"
                variant="outlined"
                size="small"
              >
                Get More Points
              </Button>
            </Box>
          </Box>
        </Container>
      </PageHeader>

      <Container maxWidth="lg">
        {!activeTab ? (
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {reportTypes.map((reportType) => (
              <Grid item xs={12} sm={6} md={3} key={reportType.type}>
                <ReportTypeCard>
                  <CardActionArea onClick={() => setActiveTab(reportType.type)}>
                    <ReportTypeContent>
                      <Typography variant="h1" sx={{ fontSize: '3rem', mb: 2 }}>
                        {reportType.icon}
                      </Typography>
                      <Typography variant="h6" gutterBottom>
                        {reportType.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        {reportType.description}
                      </Typography>
                      <PointCostChip
                        size="small"
                        icon={<StarsIcon />}
                        label={REPORT_COSTS[reportType.type]}
                      />
                    </ReportTypeContent>
                  </CardActionArea>
                </ReportTypeCard>
              </Grid>
            ))}
          </Grid>
        ) : (
          <>
            <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <Button
                onClick={() => setActiveTab(null)}
                startIcon={<HistoryIcon />}
                sx={{ mb: 2 }}
              >
                Back to Report Types
              </Button>
              <PointCostChip
                size="medium"
                icon={<StarsIcon />}
                label={`${REPORT_COSTS[activeTab]} points required`}
              />
            </Box>

            {!hasEnoughPoints() && (
              <Alert
                severity="warning"
                sx={{ mb: 3 }}
                action={
                  <Button
                    color="inherit"
                    size="small"
                    component={RouterLink}
                    to="/pricing"
                  >
                    Get Points
                  </Button>
                }
              >
                You need {REPORT_COSTS[activeTab]} points to generate this report. Your current balance: {userPoints} points.
              </Alert>
            )}

            {loading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
                <CircularProgress />
              </Box>
            ) : (
              <ReportForm
                type={activeTab}
                onSubmit={handleSubmit}
                disabled={!hasEnoughPoints()}
              />
            )}
          </>
        )}
      </Container>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          variant="filled"
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default Reports; 