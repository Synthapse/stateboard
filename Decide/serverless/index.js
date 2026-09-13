const { Client } = require('@notionhq/client');
const notion = new Client({ auth: process.env.NOTION_TOKEN });

exports.getNotionData = async (req, res) => {

  // 9.05.2025 -> Need to change this
  // Set CORS headers for preflight requests and actual responses
  res.set('Access-Control-Allow-Origin', 'http://localhost:3000'); // Change to your actual domain in production

  res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');

  // Handle preflight request
  if (req.method === 'OPTIONS') {
    return res.status(204).send('');
  }

  try {
    // Get all pages (and databases) the integration can access
    const searchResponse = await notion.search({
      sort: {
        direction: 'descending',
        timestamp: 'last_edited_time',
      },
    });

    const pages = [];
    const databases = [];

    for (const result of searchResponse.results) {
      if (result.object === 'page') {
        pages.push(result);
      } else if (result.object === 'database') {
        databases.push(result);
      }
    }

    const usersResponse = await notion.users.list();

    res.status(200).json({
      pages,
      databases,
      users: usersResponse.results,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
