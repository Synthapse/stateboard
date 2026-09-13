import { createTheme, alpha } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#0D6EFD',
      light: '#4D94FF',
      dark: '#0A58CA',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#6C757D',
      light: '#ADB5BD',
      dark: '#495057',
      contrastText: '#FFFFFF',
    },
    success: {
      main: '#198754',
      contrastText: '#FFFFFF',
    },
    info: {
      main: '#0DCAF0',
      contrastText: '#000000',
    },
    background: {
      default: '#FFFFFF',
      paper: '#F8F9FA',
    },
    text: {
      primary: '#212529',
      secondary: '#6C757D',
    },
  },
  typography: {
    fontFamily: '"Helvetica", "Arial", sans-serif',
    h1: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '3.5rem',
      fontWeight: 700,
      letterSpacing: '-0.02em',
      color: '#212529',
    },
    h2: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '2.5rem',
      fontWeight: 700,
      color: '#212529',
    },
    h3: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '2rem',
      fontWeight: 600,
      color: '#212529',
    },
    h4: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '1.5rem',
      fontWeight: 600,
      color: '#212529',
    },
    h5: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '1.25rem',
      fontWeight: 500,
      color: '#212529',
    },
    h6: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '1rem',
      fontWeight: 500,
      color: '#212529',
    },
    body1: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '1rem',
      lineHeight: 1.7,
      fontWeight: 400,
      color: '#212529',
    },
    body2: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      fontSize: '0.875rem',
      lineHeight: 1.6,
      fontWeight: 400,
      color: '#6C757D',
    },
    button: {
      fontFamily: '"Helvetica", "Arial", sans-serif',
      textTransform: 'none',
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: '10px 24px',
        },
        contained: {
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          '&:hover': {
            boxShadow: '0 6px 8px rgba(0, 0, 0, 0.15)',
          },
        },
        containedPrimary: {
          backgroundColor: '#0D6EFD',
          color: '#FFFFFF',
          '&:hover': {
            backgroundColor: '#0A58CA',
          }
        },
        outlinedPrimary: {
          borderColor: '#0D6EFD',
          color: '#0D6EFD',
          '&:hover': {
            backgroundColor: alpha('#0D6EFD', 0.04),
            borderColor: '#0A58CA',
          }
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
          border: '1px solid #DEE2E6',
          backgroundColor: '#FFFFFF',
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
          borderBottom: '1px solid #DEE2E6',
          color: '#212529',
        },
      },
    },
  },
});

export default theme; 