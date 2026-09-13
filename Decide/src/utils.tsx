
export function parseStructuredTextWithTables(text: string) {
    if (typeof text !== 'string') return { sections: [], tables: [] };

    const removeAsterisks = (str: string) => str.replace(/\*/g, '').trim();

    const lines = text.trim().split('\n');
    const sections = [];
    const tables = [];

    let currentHeader = null;
    let subpoints = [];
    let tableLines = [];
    let insideTable = false;

    const headerRegex = /^(?:\*\*|\d+\.|[IVXLCDM]+\.)\s*(.+?):?$/;
    const subpointRegex = /^\*\s*(.+?):\s*(.*)$/;
    const tableLineRegex = /^\|.*\|$/;

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (!line) continue;

        // Table handling
        if (tableLineRegex.test(line)) {
            tableLines.push(line);
            insideTable = true;
            continue;
        }

        if (insideTable && !tableLineRegex.test(line)) {
            // End of table
            if (tableLines.length >= 2) {
                const [headerLine, separatorLine, ...rowLines] = tableLines;
                const headers = headerLine.split('|').map(h => removeAsterisks(h.trim())).filter(Boolean);
                const rows = rowLines.map(row => {
                    const cols = row.split('|').map(c => removeAsterisks(c.trim()));
                    const rowObj = {};
                    // Ensure each row has the correct number of columns (align columns with headers)
                    headers.forEach((header, i) => {
                        // If a column is missing, fill it with an empty string
                        //@ts-ignore
                        rowObj[header] = cols[i + 1]; // Ensure missing columns are filled with empty string
                    });

                    return rowObj;
                });

                if (currentHeader) {
                    tables.push({ header: currentHeader, rows });
                } else {
                    tables.push({ header: '', rows });
                }
            }

            tableLines = [];
            insideTable = false;
        }

        if (insideTable) continue;

        // Header match
        const headerMatch = line.match(headerRegex);
        const subpointMatch = line.match(subpointRegex);

        if (headerMatch) {
            if (currentHeader && subpoints.length > 0) {
                sections.push({ header: currentHeader, subpoints });
                subpoints = [];
            }
            currentHeader = removeAsterisks(headerMatch[1]);
        } else if (subpointMatch) {
            subpoints.push({
                title: removeAsterisks(subpointMatch[1]),
                desc: removeAsterisks(subpointMatch[2])
            });
        }
    }

    // Push last section
    if (currentHeader && subpoints.length > 0) {
        sections.push({ header: currentHeader, subpoints });
    }

    console.log(tables);

    return { sections, tables };
}



export const parseStructuredText = (text: string) => {
    const lines = text.trim().split('\n');
    const sections: { header: string; subpoints: { title: string; desc: string }[] }[] = [];
    let currentHeader: string | null = null;
    let subpoints: { title: string; desc: string }[] = [];

    const headerRegex = /^(?:\*\*|\d+\.|[IVXLCDM]+\.)\s*(.+?):?$/;
    const subpointRegex = /^\*\s*(.+?):\s*(.*)$/;

    for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        const headerMatch = trimmed.match(headerRegex);
        const subpointMatch = trimmed.match(subpointRegex);

        if (headerMatch) {
            if (currentHeader && subpoints.length) {
                sections.push({ header: currentHeader.replace("*", ""), subpoints });
            }
            currentHeader = headerMatch[1].trim().replace("*", "");
            subpoints = [];
        } else if (subpointMatch) {
            subpoints.push({
                title: subpointMatch[1].trim().replace("**", ""),
                desc: subpointMatch[2].trim().replace("**", "").replace("*", ""),
            });
        }
    }

    if (currentHeader && subpoints.length) {
        sections.push({ header: currentHeader.replace("*", ""), subpoints });
    }

    return sections.length > 0 ? sections : null;
};