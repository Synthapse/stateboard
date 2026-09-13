import { Client } from '@notionhq/client';

// Use env — never hardcode tokens. CRA: REACT_APP_NOTION_TOKEN in Decide/.env (gitignored).
const NOTION_TOKEN = process.env.REACT_APP_NOTION_TOKEN || '';
const DATABASE_ID = process.env.REACT_APP_NOTION_DB_ID || '';

const notion = new Client({ auth: NOTION_TOKEN });

async function getDatabase() {
    const response = await notion.databases.query({
        database_id: DATABASE_ID,
    });
    return response.results;
}

export const getUsers = async () => {
	const listUsersResponse = await notion.users.list({})
    console.log(listUsersResponse)
}

export async function getNotionData() {
  if (!NOTION_TOKEN || !DATABASE_ID) {
    console.warn('Notion: set REACT_APP_NOTION_TOKEN and REACT_APP_NOTION_DB_ID');
    return null;
  }
  const res = await fetch(`https://api.notion.com/v1/databases/${DATABASE_ID}/query`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${NOTION_TOKEN}`,
      "Notion-Version": "2022-06-28",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({}) // optional filters can go here
  });

  const data = await res.json();
  console.log(data);
  return data;
}
