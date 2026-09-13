import React from 'react';
import {
  Box,
  Container,
  Typography,
  Paper,
  Button,
} from '@mui/material';
import { styled } from '@mui/material/styles';
import CancelIcon from '@mui/icons-material/Cancel';
import { useNavigate } from 'react-router-dom';

const CancelContainer = styled(Paper)(({ theme }) => ({
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

const ErrorIcon = styled(CancelIcon)(({ theme }) => ({
  fontSize: 80,
  color: theme.palette.error.main,
  marginBottom: theme.spacing(3),
}));

const StripeCancel: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Container maxWidth="lg">
      <CancelContainer>
        <ErrorIcon />
        <Typography variant="h4" gutterBottom>
          Payment Canceled
        </Typography>
        <Typography 
          variant="body1" 
          color="text.secondary" 
          align="center" 
          sx={{ maxWidth: 450, mb: 4 }}
        >
          Your payment was canceled and you have not been charged. 
          You can try again or contact our support team if you need assistance.
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
          <Button 
            variant="outlined" 
            color="primary" 
            onClick={() => navigate('/')}
          >
            Return to Home
          </Button>
          <Button 
            variant="contained" 
            color="primary" 
            onClick={() => navigate('/pricing')}
          >
            Try Again
          </Button>
        </Box>
      </CancelContainer>
    </Container>
  );
};

export default StripeCancel; 