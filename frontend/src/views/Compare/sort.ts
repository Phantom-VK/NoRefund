import type { ModelComparison, PortfolioProjection } from "@/lib/types";

/** Errored models last, then ascending total cost -- mirrors
 *  compare_view.py's `_render_results` ordering. */
export function sortResults(results: ModelComparison[]): ModelComparison[] {
  return [...results].sort((a, b) => {
    if ((a.error !== null) !== (b.error !== null)) return a.error !== null ? 1 : -1;
    return a.total_cost - b.total_cost;
  });
}

/** The cheapest model with no error, or null if every model errored. */
export function cheapestResult(results: ModelComparison[]): ModelComparison | null {
  const successful = results.filter((r) => r.error === null);
  if (successful.length === 0) return null;
  return successful.reduce((a, b) => (a.total_cost <= b.total_cost ? a : b));
}

/** Fits-in-context first, then ascending monthly cost -- matches
 *  core/portfolio.py's cheapest_that_fits(), which never picks a
 *  non-fitting model regardless of how cheap it is. */
export function sortProjections(projections: PortfolioProjection[]): PortfolioProjection[] {
  return [...projections].sort((a, b) => {
    if (a.fits_in_context !== b.fits_in_context) return a.fits_in_context ? -1 : 1;
    return a.monthly_cost - b.monthly_cost;
  });
}
