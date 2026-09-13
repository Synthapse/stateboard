import React, { useEffect } from 'react';
import {
  Typography,
  Grid,
  Box,
  Button,
  Container,
  Card,
  CardContent,
  useTheme,
  useMediaQuery,
  Divider,
  Stack
} from '@mui/material';
import { styled, keyframes, alpha } from '@mui/material/styles';
import SearchIcon from '@mui/icons-material/Search';
import PeopleIcon from '@mui/icons-material/People';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import BarChartIcon from '@mui/icons-material/BarChart';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import { auth, googleProvider } from '../firebase';
import { setPersistence, browserLocalPersistence, signInWithPopup, fetchSignInMethodsForEmail, onAuthStateChanged } from 'firebase/auth';
import { useNavigate } from 'react-router-dom';

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const HeroSection = styled(Box)(({ theme }) => ({
  background: `linear-gradient(160deg, ${alpha(theme.palette.primary.light, 0.1)} 0%, ${alpha(theme.palette.primary.main, 0.05)} 100%)`,
  color: theme.palette.text.primary,
  padding: theme.spacing(10, 0, 10),
  position: 'relative',
  overflow: 'hidden',
  '&::before': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'radial-gradient(circle at top left, rgba(100, 255, 218, 0.1), transparent 30%), radial-gradient(circle at bottom right, rgba(0, 180, 216, 0.1), transparent 30%)',
    opacity: 0.5,
    zIndex: 0,
  }
}));

const GradientText = styled(Typography)(({ theme }) => ({
  background: `linear-gradient(90deg, ${theme.palette.primary.main} 0%, ${theme.palette.info.main} 100%)`,
  WebkitBackgroundClip: 'text',
  WebkitTextFillColor: 'transparent',
  backgroundClip: 'text',
  textFillColor: 'transparent',
  animation: `${fadeIn} 1s ease-out forwards`,
}));

const HeroSubText = styled(Typography)(({ theme }) => ({
  color: theme.palette.text.secondary,
  animation: `${fadeIn} 1s ease-out 0.2s forwards`,
  opacity: 0,
}));

export const HeroButton = styled(Button)(({ theme }) => ({
  animation: `${fadeIn} 1s ease-out 0.4s forwards`,
  opacity: 0,
}));

const HeroFeatureList = styled(Box)(({ theme }) => ({
  animation: `${fadeIn} 1s ease-out 0.6s forwards`,
  opacity: 0,
}));

const HeroImageWrapper = styled(Box)(({ theme }) => ({
  animation: `${fadeIn} 1s ease-out 0.3s forwards`,
  opacity: 0,
  position: 'relative',
  zIndex: 1,
  borderRadius: theme.shape.borderRadius * 2,
  overflow: 'hidden',
  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
}));

const FeatureCard = styled(Card)(({ theme }) => ({
  height: '100%',
  background: theme.palette.background.paper,
  borderRadius: theme.spacing(2),
  border: `1px solid ${theme.palette.divider}`,
  transition: 'transform 0.3s ease-in-out, box-shadow 0.3s ease-in-out',
  boxShadow: 'none',
  '&:hover': {
    transform: 'translateY(-8px)',
    boxShadow: theme.shadows[4],
  }
}));

const IconWrapper = styled(Box)(({ theme }) => ({
  backgroundColor: alpha(theme.palette.primary.main, 0.1),
  color: theme.palette.primary.main,
  borderRadius: theme.spacing(1.5),
  width: 64,
  height: 64,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: theme.spacing(2),
}));

const FeatureList = styled(Box)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  gap: theme.spacing(2),
}));

const FeatureItem = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  gap: theme.spacing(1),
}));

const Home: React.FC = () => {

  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));

  const [logged, setLogged] = React.useState(false);

  useEffect(() => {
    // Listen for authentication state changes
    onAuthStateChanged(auth, (user) => {
      if (user) {
        setLogged(true)
      } else {
        setLogged(false)
      }
    });
  }, []);


  const signInWithGoogle = async () => {
    try {
      setPersistence(auth, browserLocalPersistence)
        .then(async () => {
          const signInCredentials = await signInWithPopup(auth, googleProvider);

          // Get the user's email
          const userEmail = signInCredentials.user.email;

          if (userEmail) {
            const signInMethods = await fetchSignInMethodsForEmail(auth, userEmail);
            const hasPassword = signInMethods.includes("password");

            if (auth) {
              navigate('/profile')
            }
          }

          return signInCredentials;
        })
        .catch((error) => {
          // Handle Errors here.
          const errorCode = error.code;
          const errorMessage = error.message;
        });
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <Box sx={{ bgcolor: 'background.default', color: 'text.primary' }}>
      {/* Hero Section */}
      <HeroSection>
        <Container maxWidth="lg">
          <Grid container spacing={6} alignItems="center">
            <Grid item xs={12} md={7}>
              <Box sx={{ position: 'relative', zIndex: 1 }}>
                <GradientText
                  variant="h1"
                  sx={{
                    fontSize: isMobile ? '2.8rem' : '4rem',
                    fontWeight: 800,
                    mb: 3,
                    letterSpacing: '-0.03em',
                    lineHeight: 1.2,
                  }}
                >
                  Unlock Audience Insights Instantly
                </GradientText>
                <HeroSubText
                  variant="h5"
                  sx={{
                    mb: 5,
                    fontWeight: 400,
                    maxWidth: '550px',
                  }}
                >
                  Aureyo leverages AI to deliver deep market understanding and competitive analysis, empowering your marketing strategy.
                </HeroSubText>
                <Box sx={{ display: 'flex', gap: 2, mb: 6 }}>
                  {!logged ? (
                    <HeroButton
                      variant="contained"
                      color="primary"
                      onClick={signInWithGoogle}
                      sx={{
                        fontWeight: 700,
                        fontSize: '1rem',
                        padding: '12px 28px',
                        transition: 'transform 0.2s ease',
                        '&:hover': {
                          transform: 'scale(1.05)',
                        }
                      }}
                      size="large"
                      endIcon={<ArrowForwardIcon />}
                    >
                      Sign in
                    </HeroButton>
                  ) : (
                    <>
                    </>
                  )}
                  <HeroButton
                    variant="outlined"
                    color="secondary"
                    sx={{
                      fontWeight: 600,
                      transition: 'background-color 0.2s ease, border-color 0.2s ease',
                      '&:hover': {
                        color: 'primary.main',
                        borderColor: 'primary.main',
                      }
                    }}
                    size="large"
                  >
                    How it Works
                  </HeroButton>
                </Box>

                <HeroFeatureList>
                  <FeatureList>
                    <FeatureItem>
                      <CheckCircleOutlineIcon color="primary" />
                      <Typography color="text.secondary">AI-powered audience research</Typography>
                    </FeatureItem>
                    <FeatureItem>
                      <CheckCircleOutlineIcon color="primary" />
                      <Typography color="text.secondary">Real-time competitor tracking</Typography>
                    </FeatureItem>
                    <FeatureItem>
                      <CheckCircleOutlineIcon color="primary" />
                      <Typography color="text.secondary">Actionable market insights</Typography>
                    </FeatureItem>
                  </FeatureList>
                </HeroFeatureList>
              </Box>
            </Grid>
            <Grid item xs={12} md={5}>
              <HeroImageWrapper>
                <Box
                  component="img"
                  src="https://images.unsplash.com/photo-1550613095-bb19738b8b4b?q=80&w=2310&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"
                  alt="Futuristic Marketing Research Speed"
                  sx={{
                    width: '100%',
                    height: 'auto',
                    display: 'block',
                  }}
                />
              </HeroImageWrapper>
            </Grid>
          </Grid>
        </Container>
      </HeroSection>

      {/* Features Section */}
      <Container maxWidth="lg" sx={{ py: 15 }}>
        <Box sx={{ textAlign: 'center', mb: 10 }}>
          <GradientText
            variant="h2"
            sx={{ fontWeight: 700, mb: 2 }}
          >
            Powerful Features for Marketing Research
          </GradientText>
          <Typography
            variant="h5"
            color="text.secondary"
            sx={{
              maxWidth: 800,
              mx: 'auto',
            }}
          >
            Everything you need to understand your audience and make data-driven decisions
          </Typography>
        </Box>

        <Grid container spacing={4}>
          <Grid item xs={12} sm={6} md={3}>
            <FeatureCard>
              <CardContent sx={{ p: 4 }}>
                <IconWrapper>
                  <SearchIcon fontSize="large" />
                </IconWrapper>
                <Typography variant="h5" component="h3" gutterBottom color="text.primary">
                  Audience Research
                </Typography>
                <Typography color="text.secondary">
                  Comprehensive tools to analyze and understand your target audience demographics and behavior.
                </Typography>
              </CardContent>
            </FeatureCard>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FeatureCard>
              <CardContent sx={{ p: 4 }}>
                <IconWrapper>
                  <PeopleIcon fontSize="large" />
                </IconWrapper>
                <Typography variant="h5" component="h3" gutterBottom color="text.primary">
                  Market Segmentation
                </Typography>
                <Typography color="text.secondary">
                  Identify and analyze market segments to target your marketing efforts effectively.
                </Typography>
              </CardContent>
            </FeatureCard>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FeatureCard>
              <CardContent sx={{ p: 4 }}>
                <IconWrapper>
                  <TrendingUpIcon fontSize="large" />
                </IconWrapper>
                <Typography variant="h5" component="h3" gutterBottom color="text.primary">
                  Competitor Analysis
                </Typography>
                <Typography color="text.secondary">
                  Stay ahead of the competition with detailed market and competitor insights.
                </Typography>
              </CardContent>
            </FeatureCard>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <FeatureCard>
              <CardContent sx={{ p: 4 }}>
                <IconWrapper>
                  <BarChartIcon fontSize="large" />
                </IconWrapper>
                <Typography variant="h5" component="h3" gutterBottom color="text.primary">
                  Data Visualization
                </Typography>
                <Typography color="text.secondary">
                  Beautiful charts and graphs to visualize your research data and insights.
                </Typography>
              </CardContent>
            </FeatureCard>
          </Grid>
        </Grid>
      </Container>

      {/* CTA Section */}
      <Box
        sx={{
          py: 10,
          bgcolor: 'background.paper',
          borderTop: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Container maxWidth="md">
          <Box
            sx={{
              textAlign: 'center',
            }}
          >
            <Typography
              variant="h3"
              sx={{ fontWeight: 700, color: 'text.primary' }}
            >
              Ready to Transform Your Marketing Research?
            </Typography>
            <Typography
              variant="h6"
              color="text.secondary"
              sx={{
                mb: 4,
                maxWidth: 600,
                mx: 'auto',
              }}
            >
              Join thousands of marketers who are already using Aureyo to make better decisions.
            </Typography>
            <Button
              variant="contained"
              color="primary"
              component="a"
              href="https://form.typeform.com/to/EnZNgIf1"
              target="_blank"
              rel="noopener noreferrer"
              sx={{
                fontWeight: 600,
                px: 4,
                py: 1.5,
              }}
              size="large"
              endIcon={<ArrowForwardIcon />}
            >
              Start Free Trial
            </Button>
          </Box>
        </Container>
      </Box>

      {/* Footer */}
      <Box sx={{ py: 4, bgcolor: 'background.paper', borderTop: `1px solid ${theme.palette.divider}` }}>
        <Container maxWidth="lg">
          <Grid container spacing={4} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h6" color="primary">
                Aureyo
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 1 }}>
                © 2023 Aureyo. All rights reserved.
              </Typography>
            </Grid>
            <Grid item xs={12} md={6}>
              <Stack direction="row" spacing={3} justifyContent={{ xs: 'center', md: 'flex-end' }}>
                <Typography color="text.secondary" sx={{ cursor: 'pointer', '&:hover': { color: 'primary.main' } }}>
                  Privacy Policy
                </Typography>
                <Typography color="text.secondary" sx={{ cursor: 'pointer', '&:hover': { color: 'primary.main' } }}>
                  Terms of Service
                </Typography>
                <Typography color="text.secondary" sx={{ cursor: 'pointer', '&:hover': { color: 'primary.main' } }}>
                  Contact Us
                </Typography>
              </Stack>
            </Grid>
          </Grid>
        </Container>
      </Box>
    </Box>
  );
};

export default Home;



{/* <a 
href="https://form.typeform.com/to/EnZNgIf1" 
target="_blank" 
rel="noopener noreferrer" 
style={{ textDecoration: 'none' }}
>
<HeroButton 
  variant="contained" 
  color="primary"
  sx={{ 
    fontWeight: 700,
    fontSize: '1rem',
    padding: '12px 28px',
    transition: 'transform 0.2s ease',
    '&:hover': {
      transform: 'scale(1.05)',
    }
  }}
  size="large"
  endIcon={<ArrowForwardIcon />}
>
  Get Started Free
</HeroButton>
</a> */}