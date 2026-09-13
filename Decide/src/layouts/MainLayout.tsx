import React, { useState, ReactNode, useEffect } from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Container,
  Box,
  IconButton,
  Menu,
  MenuItem,
  Avatar,
  useTheme,
  useMediaQuery
} from '@mui/material';
import { Link as RouterLink, useLocation } from 'react-router-dom';
import { styled } from '@mui/material/styles';
import { auth, googleProvider } from '../firebase';
import { browserLocalPersistence, fetchSignInMethodsForEmail, onAuthStateChanged, setPersistence, signInWithPopup, signOut } from 'firebase/auth';
import { useNavigate } from 'react-router-dom';
import MenuIcon from '@mui/icons-material/Menu';

const Main = styled('main')(({ theme }) => ({
  flexGrow: 1,
  paddingTop: theme.spacing(8),
  minHeight: '100vh',
}));

const LogoLink = styled(RouterLink)(({ theme }) => ({
  textDecoration: 'none',
  color: theme.palette.primary.main,
  fontWeight: 700,
  letterSpacing: '-0.5px',
}));

const NavLinks = styled('div')(({ theme }) => ({
  display: 'flex',
  gap: theme.spacing(2),
  position: 'absolute',
  left: '50%',
  transform: 'translateX(-50%)',
}));

const NavLink = styled(RouterLink)(({ theme }) => ({
  textDecoration: 'none',
  color: theme.palette.text.secondary,
  fontWeight: 500,
  '&.active': {
    color: theme.palette.primary.main,
  },
  '&:hover': {
    color: theme.palette.primary.main,
  },
}));

const Footer = styled('footer')(({ theme }) => ({
  padding: theme.spacing(2),
  backgroundColor: theme.palette.background.default,
}));

const FooterLink = styled('a')(({ theme }) => ({
  textDecoration: 'none',
  color: theme.palette.text.secondary,
  '&:hover': {
    textDecoration: 'underline',
  },
}));

const MainLayout: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [mobileMenuAnchor, setMobileMenuAnchor] = useState<null | HTMLElement>(null);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const user = auth.currentUser;

  const handleMobileMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setMobileMenuAnchor(event.currentTarget);
  };

  const handleMobileMenuClose = () => {
    setMobileMenuAnchor(null);
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleSignOut = async () => {
    try {
      await signOut(auth);
      navigate('/');
    } catch (error) {
      console.error('Error signing out:', error);
    }
    handleUserMenuClose();
  };

  const handleProfileClick = () => {
    navigate('/profile');
    handleUserMenuClose();
  };

  const isActive = (path: string) => location.pathname === path;

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


  const navItems = [
    { label: 'Home', path: '/' },
    { label: 'Features', path: '/features' },
    { label: 'Pricing', path: '/pricing' },
    ...(logged ? [
      { label: 'Generate', path: '/reports' },
      { label: 'Reports', path: '/reports/history' }
    ] : [])
  ];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static" color="default" elevation={0}>
        <Container maxWidth="lg">
          <Toolbar disableGutters sx={{ position: 'relative' }}>
            <LogoLink to="/">
              <Typography
                variant="h5"
                component="div"
                sx={{
                  fontWeight: 700,
                  color: 'primary.main',
                  letterSpacing: '-0.5px'
                }}
              >
                Aureyo
              </Typography>
            </LogoLink>

            {isMobile ? (
              <>
                <Box sx={{ flexGrow: 1 }} />
                <IconButton
                  size="large"
                  edge="end"
                  color="inherit"
                  aria-label="menu"
                  onClick={handleMobileMenuOpen}
                >
                  <MenuIcon />
                </IconButton>
                <Menu
                  anchorEl={mobileMenuAnchor}
                  open={Boolean(mobileMenuAnchor)}
                  onClose={handleMobileMenuClose}
                >
                  {navItems.map((item) => (
                    <MenuItem
                      key={item.path}
                      component={RouterLink}
                      to={item.path}
                      onClick={handleMobileMenuClose}
                      selected={isActive(item.path)}
                    >
                      {item.label}
                    </MenuItem>
                  ))}
                  {user ? (
                    <MenuItem onClick={handleSignOut}>Sign Out</MenuItem>
                  ) : (
                    <MenuItem
                      component={RouterLink}
                      to="/"
                      onClick={signInWithGoogle}
                    >
                      Sign In
                    </MenuItem>
                  )}
                </Menu>
              </>
            ) : (
              <>
                <NavLinks>
                  {navItems.map((item) => (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      className={isActive(item.path) ? 'active' : ''}
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </NavLinks>
                <Box sx={{ flexGrow: 1 }} />
                {user ? (
                  <>
                    <IconButton
                      onClick={handleUserMenuOpen}
                      size="small"
                      sx={{ ml: 2 }}
                    >
                      <Avatar
                        src={user.photoURL || undefined}
                        alt={user.displayName || 'User'}
                        sx={{ width: 32, height: 32 }}
                      />
                    </IconButton>
                    <Menu
                      anchorEl={userMenuAnchor}
                      open={Boolean(userMenuAnchor)}
                      onClose={handleUserMenuClose}
                    >
                      <MenuItem onClick={handleProfileClick}>Profile</MenuItem>
                      <MenuItem onClick={handleSignOut}>Sign Out</MenuItem>
                    </Menu>
                  </>
                ) : (
                  <Button
                    component={RouterLink}
                    to="/"
                    variant="contained"
                    color="primary"
                    onClick={signInWithGoogle}
                  >
                    Sign In
                  </Button>
                )}
              </>
            )}
          </Toolbar>
        </Container>
      </AppBar>

      <Box component="main" sx={{ flexGrow: 1 }}>
        {children}
      </Box>

      <Footer>
        <Container maxWidth="lg">
          <Box sx={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 2
          }}>
            <Typography variant="body2" color="text.secondary">
              © 2024 Aureyo. All rights reserved.
            </Typography>
            <Box sx={{ display: 'flex', gap: 3 }}>
              <FooterLink href="#" target="_blank" rel="noopener noreferrer">
                Privacy Policy
              </FooterLink>
              <FooterLink href="#" target="_blank" rel="noopener noreferrer">
                Terms of Service
              </FooterLink>
            </Box>
          </Box>
        </Container>
      </Footer>
    </Box>
  );
};

export default MainLayout; 