import React, { useEffect, useState } from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
  CircularProgress,
  Divider,
  Chip
} from '@mui/material';
import { styled } from '@mui/material/styles';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import StarsIcon from '@mui/icons-material/Stars';
import { useNavigate } from 'react-router-dom';
import config from '../config.json';
import axios from 'axios';
import { auth } from '../firebase';
import { savePointsFromSubscription, saveUserSubscription } from 'services/subscriptionService';

export interface PaymentIntentSucceed {
  id: string;
  created: Date;
  currency: string;
  customerId: string;
  customerEmail: string;
  amount: number;
  products: any;
}

const SuccessContainer = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(6),
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  maxWidth: 600,
  margin: '0 auto',
  marginTop: theme.spacing(8),
  marginBottom: theme.spacing(8),
  borderRadius: theme.spacing(2),
  boxShadow: theme.shadows[3],
}));

const SuccessIcon = styled(CheckCircleIcon)(({ theme }) => ({
  fontSize: 80,
  color: theme.palette.success.main,
  marginBottom: theme.spacing(3),
}));

const PointsDisplay = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: 'rgba(255, 215, 0, 0.1)',
  borderRadius: theme.spacing(2),
  padding: theme.spacing(2, 4),
  margin: theme.spacing(4, 0),
}));

const PointsIcon = styled(StarsIcon)(({ theme }) => ({
  color: '#FFD700',
  marginRight: theme.spacing(1),
  fontSize: 28,
}));

const StripeSuccess: React.FC = () => {
  const [processingPayment, setProcessingPayment] = useState(true);
  const [pointsAdded, setPointsAdded] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();


  const getUserEmailFromUrl = () => {
    const hashIndex = window.location.href.indexOf('#');
    if (hashIndex !== -1) {
      const queryString = window.location.href.substr(hashIndex + 1).split('?')[1];
      if (queryString) {
        const urlSearchParams = new URLSearchParams(queryString);
        return urlSearchParams.get('userEmail');
      }
    }
    return null;
  };



  const saveSubscription = (userEmail: string, data: PaymentIntentSucceed) => {

      const points = data.products[0].quantity;

      const subscriptionData = {
        id: data.id,
        created: data.created,
        amountTotal: data.amount,
        currency: data.currency,
        customerEmail: data.customerEmail,
        customerId: data.customerId,
        description: data.products[0].description,
        quantity: points, 
      }

      setPointsAdded(points);
      console.log(`Save data for ${userEmail}, with ${subscriptionData}`)
      saveUserSubscription(userEmail, subscriptionData);
      savePointsFromSubscription(userEmail, points);
    
      setProcessingPayment(false);
  }


  const processSubscription = () => {
    const userEmail = getUserEmailFromUrl();
    const url = `${config.apps.PaymentAPI.url}/Payment/finalizePayment?userEmail=${userEmail}`;

    axios.get(url)
      .then(response => {
        saveSubscription(userEmail ?? "", response.data)
      })
      .catch(error => {
        // Handle error
        console.error('Error:', error);
      });
  };


  useEffect(() => {
    processSubscription();
  }, [])



  const handleContinue = () => {
    navigate('/reports');
  };

  return (
    <Container maxWidth="lg">
      <SuccessContainer>
        {processingPayment ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <CircularProgress size={60} sx={{ mb: 3 }} />
            <Typography variant="h5" gutterBottom>
              Processing your payment...
            </Typography>
            <Typography color="text.secondary">
              Please wait while we confirm your payment.
            </Typography>
          </Box>
        ) : error ? (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="h5" color="error" gutterBottom>
              Payment Error
            </Typography>
            <Typography paragraph>
              {error}
            </Typography>
            <Button
              variant="contained"
              color="primary"
              onClick={() => navigate('/pricing')}
            >
              Return to Pricing
            </Button>
          </Box>
        ) : (
          <>
            <SuccessIcon />
            <Typography variant="h4" gutterBottom>
              Payment Successful!
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              align="center"
              paragraph
            >
              Thank you for your purchase. Your points have been added to your account.
            </Typography>

            <Divider sx={{ width: '100%', my: 3 }} />

            <Typography variant="h6" gutterBottom>
              Points Added to Your Account
            </Typography>

            <PointsDisplay>
              <PointsIcon />
              <Typography
                variant="h4"
                component="span"
                sx={{ fontWeight: 700 }}
              >
                {pointsAdded} Points
              </Typography>
            </PointsDisplay>

            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <Button
                variant="outlined"
                color="primary"
                onClick={() => navigate('/profile')}
              >
                Go to Profile
              </Button>
              <Button
                variant="contained"
                color="primary"
                onClick={handleContinue}
              >
                Start Creating Reports
              </Button>
            </Box>
          </>
        )}
      </SuccessContainer>
    </Container>
  );
};

export default StripeSuccess; 