import { expect, test } from '@playwright/test';

const png = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=',
  'base64',
);

test('creates a tenant-scoped artwork and securely uploads its primary image', async ({ page }) => {
  const slug = `e2e-gallery-${Date.now()}`;
  const artworkTitle = `E2E Verifiable Study ${Date.now()}`;
  await page.goto('/app');
  const organizationName = page.getByLabel('Organization name');
  if (await organizationName.isVisible()) {
    await organizationName.fill('E2E Gallery');
    await page.getByLabel('Workspace URL key').fill(slug);
    await page.getByRole('button', { name: /Create secure workspace/i }).click();
  }

  await expect(page.getByRole('heading', { name: 'Command Center' })).toBeVisible();
  await page.getByRole('link', { name: 'Artwork Registry', exact: true }).click();
  await page.getByRole('button', { name: /Register artwork/i }).click();
  await page.getByLabel('Artwork title *').fill(artworkTitle);
  await page.getByLabel('Claimed artist attribution').fill('Test fixture artist');
  await page.getByLabel('Medium').fill('PNG test fixture');
  await page.locator('input[type="file"]').setInputFiles({
    name: 'authorized-fixture.png',
    mimeType: 'image/png',
    buffer: png,
  });
  await page.getByRole('button', { name: /Create artwork record/i }).click();

  await expect(page.getByRole('heading', { name: artworkTitle })).toBeVisible();
  await expect(page.getByText('SHA-256 file fingerprint')).toBeVisible();
  await expect(page.getByText(/Identifies these bytes—not authenticity/i)).toBeVisible();
});
