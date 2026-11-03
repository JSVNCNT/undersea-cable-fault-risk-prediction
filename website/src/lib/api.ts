import { z } from 'zod';
import release from '../release.json';
const apiUrl = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
const predictionSchema = z.object({
  prediction: z.number().int().min(0).max(1),
  positive_class_score: z.number().min(0).max(1),
  model: z.literal('random_forest'),
  model_sha256: z.literal(release.model_sha256),
  release_id: z.literal(release.release_id),
  decision_rule: z.string(),
  warnings: z.array(z.string()),
  limitation: z.string(),
});
export type Prediction = z.infer<typeof predictionSchema>;
export const apiConfigured = Boolean(apiUrl);
async function request(path: string, init: RequestInit = {}) {
  if (!apiUrl)
    throw new Error(
      'Prediction service unavailable. Configure VITE_API_URL to connect the Python service.',
    );
  let response: Response;
  try {
    response = await fetch(`${apiUrl}${path}`, { ...init, signal: AbortSignal.timeout(20000) });
  } catch {
    throw new Error(
      'Prediction service unavailable. Check the connection or allow the backend to finish starting, then recheck. No prediction was produced.',
    );
  }
  if (!response.ok) {
    if (response.status === 429)
      throw new Error(
        'Prediction service is busy or the demonstration limit was reached. Try again shortly.',
      );
    if (response.status === 422)
      throw new Error(
        'Some inputs were rejected. Check all fields and the published category options.',
      );
    throw new Error('Prediction service unavailable. No prediction was produced.');
  }
  return response.json() as Promise<unknown>;
}
export async function checkHealth() {
  const data = await request('/api/health');
  z.object({
    status: z.literal('ready'),
    model_sha256: z.literal(release.model_sha256),
    release_id: z.literal(release.release_id),
  }).parse(data);
}
export async function predict(values: Record<string, string | number>): Promise<Prediction> {
  return predictionSchema.parse(
    await request('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    }),
  );
}
