import { expect, test } from '@playwright/test'

test('demo planner can sign in, reach operations and sign out', async ({ page }) => {
  await page.goto('/login')

  await page.getByRole('button', { name: 'Usar acesso demo' }).click()
  await page.getByRole('button', { name: 'Entrar' }).click()

  await expect(page.getByRole('heading', { name: 'Operações' })).toBeVisible()
  await expect(page.getByText('Planejador Demo')).toBeVisible()
  await expect(page.getByRole('link', { name: /Configurações/ })).toHaveCount(0)

  await page.getByRole('button', { name: 'Sair' }).click()
  await expect(page.getByRole('heading', { name: 'Acesse o FluxMed' })).toBeVisible()
})
