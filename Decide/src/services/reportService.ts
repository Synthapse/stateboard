import axios from 'axios';
import { MarketingStrategyReport, EarlyAdaptersDesignReport, GoToMarketReport, RedditAudienceReport } from '../types/reports';
import config from '../config.json'

const API_BASE_URL = config.apps.RaportingAPI.url;
const MAS_BASE_URL = config.apps.MASAPI.url;

export const generateMarketingStrategyReport = async (data: MarketingStrategyReport) => {
  const response = await axios.post(`${API_BASE_URL}/marketing-strategy`, data);
  return response.data;
};

export const generateEarlyAdaptersReport = async (data: EarlyAdaptersDesignReport) => {
  const response = await axios.post(`${API_BASE_URL}/early-adopter-strategy`, data);
  return response.data;
};

export const generateGoToMarketReport = async (data: GoToMarketReport) => {
  const response = await axios.post(`${API_BASE_URL}/go-to-market`, data);
  return response.data;
};

export const generateRedditAudienceReport = async (community: string) => {
  const url = `${MAS_BASE_URL}/analysis/community?community=${community}`
  //const url = `http://localhost:8000/analysis/community?community=${community}`;

  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ community }),
    });

    console.log(response);
    // Check if the response is successful
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response?.body?.getReader();
    const decoder = new TextDecoder();
    let result = '';

    // Process the stream chunks
    while (true) {
      //@ts-ignore
      const { done, value } = await reader?.read();
      if (done) {
        break; // End of stream
      }
      console.log(value);
      console.log(done, value);
      result += decoder.decode(value, { stream: true });
    }

    // Parse the final result (the complete JSON string)
    const reports = JSON.parse(result);

    return {
      "pdf_document": null,
      "text_content": reports,
    };

  } catch (error) {
    console.error('Error generating Reddit audience report:', error);
    throw error;
  }
};
