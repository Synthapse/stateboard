import type { CostOptions, PriceQuery, UnitPrice } from '../types.js';
import awsBook from './pricebooks/aws.json' with { type: 'json' };
import azureBook from './pricebooks/azure.json' with { type: 'json' };
import gcpBook from './pricebooks/gcp.json' with { type: 'json' };

type Book = {
  asOf: string;
  compute?: Record<string, Record<string, number>>;
  disk?: Record<string, Record<string, number>>;
  database?: Record<string, Record<string, number>>;
  network?: Record<string, Record<string, number>>;
  object?: Record<string, Record<string, number>>;
};

const BOOKS: Record<'aws' | 'azure' | 'gcp', Book> = {
  aws: awsBook as Book,
  azure: azureBook as Book,
  gcp: gcpBook as Book,
};

function fromBook(query: PriceQuery): UnitPrice | null {
  const book = BOOKS[query.cloud];
  const regionTable = book[query.family === 'free' || query.family === 'other' ? 'compute' : query.family];
  if (!regionTable) return null;
  const region = regionTable[query.region] ?? Object.values(regionTable)[0];
  if (!region) return null;
  const amount = region[query.sku];
  if (amount == null) return null;

  const unit =
    query.family === 'compute' || query.family === 'database'
      ? 'hour'
      : query.family === 'disk' || query.family === 'object'
        ? 'gb-month'
        : 'month';

  return { amount, unit, source: 'pricebook', asOf: book.asOf };
}

export async function getUnitPrice(
  query: PriceQuery,
  options: CostOptions,
): Promise<UnitPrice | null> {
  const mode = options.priceSource ?? 'local';

  if (mode === 'live' || mode === 'local+live') {
    if (options.fetchPrices) {
      const live = await options.fetchPrices(query);
      if (live) return live;
    }
    if (mode === 'live') return null;
  }

  return fromBook(query);
}

export function bookAsOf(): string {
  return awsBook.asOf;
}
