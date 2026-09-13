export interface MarketingStrategyReport {
  title: string;
  objectives: string;
  strategic_prompt: string;
  target_market: string;
  budget_constraints: string;
}

export interface EarlyAdaptersDesignReport {
  title: string;
  product_description: string;
  target_audience: string;
  strategic_goals: string;
  resource_constraints: string;
}

export interface GoToMarketReport {
  title: string;
  product_description: string;
  target_market: string;
  budget_range: string;
  timeline_constraints: string;
}

export interface RedditAudienceReport {
  title: string;
  community: string;
}

export type ReportType = 'marketing-strategy' | 'early-adapters' | 'go-to-market' | 'reddit-audience'; 