import React from 'react';
import { 
  Typography, 
  Box, 
  Container,
  Grid,
  Paper,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  useTheme,
  alpha
} from '@mui/material';
import { styled } from '@mui/material/styles';
import IntegrationInstructionsIcon from '@mui/icons-material/IntegrationInstructions';
import QueryStatsIcon from '@mui/icons-material/QueryStats';
import InsightsIcon from '@mui/icons-material/Insights';
import PresentToAllIcon from '@mui/icons-material/PresentToAll';

const PageHeader = styled(Box)(({ theme }) => ({
  background: theme.palette.background.paper,
  padding: theme.spacing(10, 0, 8),
  marginBottom: theme.spacing(8),
  textAlign: 'center',
  borderBottom: `1px solid ${theme.palette.divider}`,
}));

const StepIconWrapper = styled(Box)(({ theme }) => ({
  backgroundColor: theme.palette.primary.main,
  color: theme.palette.primary.contrastText,
  borderRadius: '50%',
  width: 40,
  height: 40,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  boxShadow: `0 4px 10px ${alpha(theme.palette.primary.main, 0.25)}`,
}));

const steps = [
  {
    label: 'Define Your Research Goals',
    description: `Start by clearly defining what you want to learn about your target audience. Are you exploring demographics, understanding pain points, or analyzing competitor positioning? Setting clear goals guides your research process within Aureyo.`,
    icon: <IntegrationInstructionsIcon />,
  },
  {
    label: 'Input Your Criteria & Keywords',
    description: `Leverage Aureyo's intuitive interface to input your research parameters. Use specific keywords, demographic filters, and industry sectors to focus the AI's search and analysis. The more precise your input, the more relevant the insights.`,
    icon: <QueryStatsIcon />,
  },
  {
    label: 'AI Analyzes Data Sources',
    description: `Aureyo's powerful AI engine scans millions of data points from diverse sources, including social media, forums, surveys, and market reports. It identifies patterns, sentiments, and key trends relevant to your criteria.`,
    icon: <InsightsIcon />,
  },
  {
    label: 'Receive Actionable Insights & Reports',
    description: `Get comprehensive reports with clear visualizations, summaries, and actionable insights. Understand audience segments, competitor strategies, and market opportunities easily. Export reports in various formats to share with your team.`,
    icon: <PresentToAllIcon />,
  },
];

const HowItWorks: React.FC = () => {
  const theme = useTheme();

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
              color: 'primary.main'
            }}
          >
            How Aureyo Works
          </Typography>
          <Typography 
            variant="h5" 
            sx={{ color: 'text.secondary', maxWidth: 600, mx: 'auto' }}
          >
            Discover audience insights in four simple steps using our powerful AI-driven platform.
          </Typography>
        </Container>
      </PageHeader>

      <Container maxWidth="lg" sx={{ pb: 10 }}>
        <Stepper orientation="vertical" sx={{ 
          '& .MuiStepConnector-line': {
            borderColor: theme.palette.divider,
          }
         }}>
          {steps.map((step, index) => (
            <Step key={step.label} active={true}>
              <StepLabel
                StepIconComponent={() => (
                  <StepIconWrapper>
                    {step.icon}
                  </StepIconWrapper>
                )}
              >
                <Typography variant="h5" component="h3" sx={{ fontWeight: 600, color: 'text.primary' }}>
                  {step.label}
                </Typography>
              </StepLabel>
              <StepContent sx={{ 
                borderColor: theme.palette.divider,
                ml: 2.5,
                pl: 3,
                borderLeftWidth: '1px',
               }}>
                <Typography sx={{ color: 'text.secondary' }}>{step.description}</Typography>
              </StepContent>
            </Step>
          ))}
        </Stepper>
      </Container>
    </Box>
  );
};

export default HowItWorks; 