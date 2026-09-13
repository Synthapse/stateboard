import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Grid,
  Card,
  CardContent,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Button,
  useTheme,
  useMediaQuery,
  Slider,
  Divider,
  Paper,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import StarsIcon from '@mui/icons-material/Stars';
import { styled } from '@mui/material/styles';
import config from 'config.json';
import axios from 'axios';
import { auth, googleProvider } from '../firebase';
import { browserLocalPersistence, fetchSignInMethodsForEmail, onAuthStateChanged, setPersistence, signInWithPopup } from 'firebase/auth';
import { useNavigate, useNavigation } from 'react-router-dom';
import { HeroButton } from './Home';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';

const plans = [
  {
    name: 'Points Package',
    description: 'Generate comprehensive marketing and business strategy documents with our AI-powered platform',
    pricePerPoint: 0.25,
    features: [
      'Generate Marketing Strategy Reports',
      'Create Go-to-Market Documents',
      'Analyze Early Adopters',
      'Access to AI-powered insights',
      'Export reports in multiple formats',
      'Save and manage report history',
      'Customizable report templates',
      'Real-time market analysis',
      'Competitor analysis',
      'Audience segmentation',
      'Market opportunity assessment'
    ],
  },
];

const PointsIcon = styled(StarsIcon)(({ theme }) => ({
  color: '#FFD700',
  marginRight: theme.spacing(1),
}));

const PointsDisplay = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  marginBottom: theme.spacing(2),
}));

const PricingCard = styled(Card)(({ theme }) => ({
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease-in-out',
  '&:hover': {
    transform: 'translateY(-8px)',
  },
}));

const SliderContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  marginTop: theme.spacing(2),
  marginBottom: theme.spacing(3),
  borderRadius: theme.spacing(2),
  background: theme.palette.background.paper,
}));

const pointMarks = [
  { value: 5, label: '5' },
  { value: 10, label: '10' },
  { value: 25, label: '25' },
  { value: 50, label: '50' },
  { value: 100, label: '100' },
];

const Pricing: React.FC = () => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const navigate = useNavigate()
  const [selectedPoints, setSelectedPoints] = useState<number>(10);

  const handlePointsChange = (event: Event, newValue: number | number[]) => {
    setSelectedPoints(newValue as number);
  };

  const calculatePrice = (points: number) => {
    let pricePerPoint = plans[0].pricePerPoint;

    // Apply discount for larger packages
    if (points >= 50) {
      pricePerPoint = 0.18; // 20% discount for 50+ points
    } else if (points >= 25) {
      pricePerPoint = 0.20; // 10% discount for 25+ points
    }

    return (points * pricePerPoint)
  };


  const userEmail = auth.currentUser?.email;

  const startPayment = () => {
    const data = {
      Url: window.location.href.toString(),
      Email: userEmail,
      Points: selectedPoints,
      Price: Number(calculatePrice(selectedPoints))
    }

    console.log(data)

    axios.post(`${config.apps.PaymentAPI.url}/Payment/buyAureyoPoints`, data)
      .then(response => {
        // Handle success
        console.log(response);
        window.open(response.data, '_blank')
        console.log('Response:', response.data);
      })
      .catch(error => {
        // Handle error
        console.error('Error:', error);
      })
  }


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

  return (
    <Box sx={{ bgcolor: 'background.default', py: 8 }}>
      <Container maxWidth="lg">
        <Grid container spacing={4} justifyContent="center">
          {plans.map((plan) => (
            <Grid
              sx={{ display: 'flex', flexDirection: { xs: 'column', lg: 'row' }, alignItems: 'flex-start' }}
              item xs={12} sm={10} md={10} lg={12}
              key={plan.name}
            >
              <List sx={{ mb: 4, flex: { lg: 1 } }}>
                {plan.features.map((feature) => (
                  <ListItem key={feature} sx={{ py: 1 }}>
                    <ListItemIcon>
                      <CheckCircleIcon color="primary" />
                    </ListItemIcon>
                    <ListItemText primary={feature} />
                  </ListItem>
                ))}
              </List>

              <PricingCard sx={{ flex: { lg: 1 }, minWidth: { xs: '100%', lg: '400px' } }}>
                <CardContent sx={{ p: 4, flexGrow: 1 }}>
                  <Typography
                    variant="h4"
                    component="h2"
                    gutterBottom
                    sx={{ fontWeight: 700, color: 'primary.main' }}
                  >
                    {plan.name}
                  </Typography>

                  <SliderContainer elevation={0}>
                    <Typography variant="h6" gutterBottom>
                      Select Points to Purchase
                    </Typography>

                    <Slider
                      value={selectedPoints}
                      onChange={handlePointsChange}
                      step={null}
                      marks={pointMarks}
                      min={5}
                      max={100}
                      valueLabelDisplay="auto"
                      aria-labelledby="points-slider"
                    />

                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: 2 }}>
                      <Typography variant="body2" color="text.secondary">
                        5 points
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        100 points
                      </Typography>
                    </Box>
                  </SliderContainer>

                  <Divider sx={{ my: 2 }} />

                  <PointsDisplay>
                    <PointsIcon sx={{ fontSize: 28 }} />
                    <Typography variant="h4" component="span" sx={{ fontWeight: 700 }}>
                      {selectedPoints} Points
                    </Typography>
                  </PointsDisplay>

                  <Typography
                    variant="h3"
                    component="div"
                    gutterBottom
                    align="center"
                    sx={{ fontWeight: 700, mb: 2 }}
                  >
                    ${calculatePrice(selectedPoints)}
                  </Typography>

                  <Typography
                    variant="body2"
                    color="text.secondary"
                    paragraph
                    align="center"
                    sx={{ mb: 4 }}
                  >
                    {selectedPoints >= 25 ? 'Discount applied!' : 'Buy more points for a discount'}
                  </Typography>
                  {!logged ?
                    <>
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
                    </>
                    :
                    <Button
                      variant="contained"
                      color="primary"
                      fullWidth
                      onClick={startPayment}
                      size="large"
                      sx={{ mt: 'auto' }}
                    >
                      Buy {selectedPoints} Points
                    </Button>
                  }
                </CardContent>
              </PricingCard>
            </Grid>
          ))}
        </Grid>
      </Container>
    </Box>
  );
};

export default Pricing; 