import { test, expect } from '@playwright/test'

test('register -> login -> exam -> stats', async ({ page }) => {
  const email = `ui_${Date.now()}@example.com`
  const password = 'Password123'

  await page.goto('/register')
  await page.getByLabel('Имя').fill('UI Tester')
  await page.getByLabel('Email').fill(email)
  await page.getByLabel('Пароль').fill(password)
  await page.getByRole('button', { name: 'Создать аккаунт' }).click()

  await expect(page).toHaveURL(/\/app$/)
  await expect(page.getByRole('heading', { name: 'Главная' })).toBeVisible()

  await page.getByRole('link', { name: 'Экзамены' }).click()
  await expect(page).toHaveURL(/\/app\/exams$/)
  await expect(page.getByRole('heading', { name: 'Экзамены' })).toBeVisible()

  const e2eCard = page.locator('.card').filter({ hasText: 'E2E UI Theme' })
  await expect(e2eCard.first()).toBeVisible()
  await e2eCard.first().getByRole('button', { name: 'Начать' }).click()

  await expect(page).toHaveURL(/\/app\/exams\//)
  await expect(page.getByText('Вопрос')).toBeVisible()
  await page.getByLabel('Ваш ответ').fill('42')
  await page.getByRole('button', { name: 'Отправить ответ' }).click()

  await page.getByRole('link', { name: 'Статистика' }).click()
  await expect(page).toHaveURL(/\/app\/stats$/)
  await expect(page.getByRole('heading', { name: 'Статистика' })).toBeVisible()
  await expect(page.getByText('Всего ответов:')).toBeVisible()
})
