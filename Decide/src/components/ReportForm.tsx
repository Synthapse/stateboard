import React, { useState } from 'react';
import { Box, Button, TextField, Typography, Paper, Stack, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { MarketingStrategyReport, EarlyAdaptersDesignReport, GoToMarketReport, RedditAudienceReport, ReportType } from '../types/reports';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';

type ReportFormProps = {
  type: ReportType;
  onSubmit: (data: MarketingStrategyReport | EarlyAdaptersDesignReport | GoToMarketReport | RedditAudienceReport) => void;
  disabled?: boolean;
};

const sampleData = {
  'marketing-strategy': {
    title: 'Q2 2024 Digital Marketing Strategy',
    objectives: 'Increase online presence and engagement by 50%, boost conversion rates by 25%, and establish brand authority in the tech industry.',
    strategic_prompt: 'Develop a comprehensive digital marketing strategy focusing on content marketing, social media engagement, and targeted advertising campaigns.',
    target_market: 'Tech-savvy professionals aged 25-45, working in software development and IT industries, with high interest in productivity tools.',
    budget_constraints: 'Monthly budget of $10,000 with 40% allocated to paid advertising, 30% to content creation, and 30% to marketing tools and analytics.',
  },
  'early-adapters': {
    title: 'SaaS Platform Early Adopters Program',
    product_description: 'Cloud-based project management tool with AI-powered task automation and team collaboration features.',
    target_audience: 'Startup founders and small business owners in the technology sector, particularly those managing remote teams.',
    strategic_goals: 'Gather detailed user feedback, achieve 80% user retention rate, and collect 50 testimonials within the first three months of launch.',
    resource_constraints: 'Limited development team capacity (5 developers), marketing budget of $5,000 per month, and 6-month timeline for program completion.',
  },
  'go-to-market': {
    title: 'AI-Powered Analytics Platform Launch',
    product_description: 'Enterprise-level analytics platform leveraging artificial intelligence for real-time business insights and predictive analysis.',
    target_market: 'Medium to large-sized businesses in finance, retail, and healthcare sectors with annual revenue exceeding $10M.',
    budget_range: '$500,000 initial launch budget with $100,000 monthly operational budget for the first year.',
    timeline_constraints: '6 months for beta testing, 3 months for market validation, and full market launch within 12 months.',
  },
  'reddit-audience': {
    title: 'r/startups Community Analysis',
    community: 'r/startups',
  }
};

const budgetOptions = [
  { value: 'free', label: 'No budget, just time' },
  { value: 'small', label: 'Small ($1,000 - $5,000 monthly)' },
  { value: 'medium', label: 'Medium ($5,000 - $20,000 monthly)' },
  { value: 'large', label: 'Large ($20,000+ monthly)' },
  { value: 'custom', label: 'Custom Budget' }
];

const timelineOptions = [
  { value: 'short', label: 'Short Term (1-3 months)' },
  { value: 'medium', label: 'Medium Term (3-6 months)' },
  { value: 'long', label: 'Long Term (6-12 months)' },
  { value: 'custom', label: 'Custom Timeline' }
];

const getInitialFormData = (type: ReportType) => {
  const baseData = { title: '' };
  
  switch (type) {
    case 'marketing-strategy':
      return {
        ...baseData,
        objectives: '',
        strategic_prompt: 'Develop a comprehensive digital marketing strategy focusing on content marketing, social media engagement, and targeted advertising campaigns.',
        target_market: '',
        budget_constraints: 'medium',
      };
    case 'early-adapters':
      return {
        ...baseData,
        product_description: '',
        target_audience: '',
        strategic_goals: '',
        resource_constraints: 'medium',
      };
    case 'go-to-market':
      return {
        ...baseData,
        product_description: '',
        target_market: '',
        budget_range: 'medium',
        timeline_constraints: 'medium',
      };
    case 'reddit-audience':
      return {
        ...baseData,
        community: '',
      };
  }
};

const getFormFields = (type: ReportType) => {
  switch (type) {
    case 'marketing-strategy':
      return [
        { name: 'title', label: 'Title' },
        { name: 'objectives', label: 'Objectives' },
        // { name: 'strategic_prompt', label: 'Strategic Prompt' },
        { name: 'target_market', label: 'Target Market' },
        { name: 'budget_constraints', label: 'Budget Constraints' },
      ];
    case 'early-adapters':
      return [
        { name: 'title', label: 'Title' },
        { name: 'product_description', label: 'Product Description' },
        { name: 'target_audience', label: 'Target Audience' },
        { name: 'strategic_goals', label: 'Strategic Goals' },
        // { name: 'resource_constraints', label: 'Resource Constraints' },
      ];
    case 'go-to-market':
      return [
        { name: 'title', label: 'Title' },
        { name: 'product_description', label: 'Product Description' },
        { name: 'target_market', label: 'Target Market' },
        { name: 'budget_range', label: 'Budget Range' },
        { name: 'timeline_constraints', label: 'Timeline Constraints' },
      ];
    case 'reddit-audience':
      return [
        { name: 'title', label: 'Title' },
        { name: 'community', label: 'Reddit Community' },
      ];
  }
};

const ReportForm: React.FC<ReportFormProps> = ({ type, onSubmit, disabled = false }) => {
  const [formData, setFormData] = useState(getInitialFormData(type));
  const [showCustomBudget, setShowCustomBudget] = useState(false);
  const [showCustomTimeline, setShowCustomTimeline] = useState(false);
  
  // Update form data when type changes
  React.useEffect(() => {
    setFormData(getInitialFormData(type));
  }, [type]);

  const handleChange = (field: string) => (event: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({
      ...prev,
      [field]: event.target.value,
    }));
  };

  const handleSelectChange = (field: string) => (event: any) => {
    const value = event.target.value;
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));

    if (field === 'budget_constraints' || field === 'budget_range') {
      setShowCustomBudget(value === 'custom');
    }
    if (field === 'timeline_constraints') {
      setShowCustomTimeline(value === 'custom');
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!disabled) {
      onSubmit(formData);
    }
    // Not clearing the form data here, so it's preserved if there's an error
  };

  const fillWithExample = () => {
    setFormData(sampleData[type]);
  };

  const clearForm = () => {
    setFormData(getInitialFormData(type));
  };

  const fields = getFormFields(type);
  const formTitle = type.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');

  return (
    <Paper elevation={3} sx={{ p: 3, maxWidth: 600, mx: 'auto', mt: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" component="h2">
          {formTitle} Report
        </Typography>
        <Box>
          <Button
            variant="outlined"
            color="primary"
            startIcon={<AutoFixHighIcon />}
            onClick={fillWithExample}
            size="small"
            sx={{ mr: 1 }}
            disabled={disabled}
          >
            Fill with Example
          </Button>
          <Button
            variant="text"
            color="secondary"
            onClick={clearForm}
            size="small"
            disabled={disabled}
          >
            Clear
          </Button>
        </Box>
      </Box>
      <Box component="form" onSubmit={handleSubmit} sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {fields.map(field => {
          if (field.name === 'budget_constraints' || field.name === 'budget_range') {
            return (
              <Box key={field.name}>
                <FormControl fullWidth required>
                  <InputLabel>{field.label}</InputLabel>
                  <Select
                    value={formData[field.name as keyof typeof formData]}
                    onChange={handleSelectChange(field.name)}
                    label={field.label}
                    disabled={disabled}
                  >
                    {budgetOptions.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                {showCustomBudget && (
                  <TextField
                    label="Custom Budget Details"
                    value={formData[field.name as keyof typeof formData]}
                    onChange={handleChange(field.name)}
                    fullWidth
                    required
                    multiline
                    rows={3}
                    disabled={disabled}
                    sx={{ mt: 2 }}
                  />
                )}
              </Box>
            );
          }
          
          if (field.name === 'timeline_constraints') {
            return (
              <Box key={field.name}>
                <FormControl fullWidth required>
                  <InputLabel>{field.label}</InputLabel>
                  <Select
                    value={formData[field.name as keyof typeof formData]}
                    onChange={handleSelectChange(field.name)}
                    label={field.label}
                    disabled={disabled}
                  >
                    {timelineOptions.map(option => (
                      <MenuItem key={option.value} value={option.value}>
                        {option.label}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
                {showCustomTimeline && (
                  <TextField
                    label="Custom Timeline Details"
                    value={formData[field.name as keyof typeof formData]}
                    onChange={handleChange(field.name)}
                    fullWidth
                    required
                    multiline
                    rows={3}
                    disabled={disabled}
                    sx={{ mt: 2 }}
                  />
                )}
              </Box>
            );
          }

          return (
            <TextField
              key={field.name}
              label={field.label}
              value={formData[field.name as keyof typeof formData]}
              onChange={handleChange(field.name)}
              fullWidth
              required
              multiline={field.name !== 'title'}
              rows={field.name !== 'title' ? 3 : 1}
              disabled={disabled}
            />
          );
        })}
        <Button
          type="submit"
          variant="contained"
          color="primary"
          sx={{ mt: 2 }}
          disabled={disabled}
        >
          Generate Report
        </Button>
      </Box>
    </Paper>
  );
};

export default ReportForm; 