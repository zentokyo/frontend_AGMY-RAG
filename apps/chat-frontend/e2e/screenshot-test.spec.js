import { test, expect } from '@playwright/test'
import { join } from 'path'

const STUDENT_BASE_URL = process.env.STUDENT_BASE_URL || 'http://127.0.0.1:4174'
const ADMIN_BASE_URL = process.env.ADMIN_BASE_URL || 'http://127.0.0.1:8001'

function appUrl(baseUrl, path) {
  return new URL(path, baseUrl).toString()
}

test('full manual flow and screenshots', async ({ browser }) => {
  const screenshotsDir = '/Users/elvsevolod/CursorProject/frontend_AGMY-RAG/screenshots'

  // 1. --- STUDENT PORTAL ---
  console.log('Testing Student Portal...')
  const studentContext = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  })
  const studentPage = await studentContext.newPage()
  
  const studentEmail = `student_${Date.now()}@example.com`
  const password = 'Password123'

  // Register
  await studentPage.goto(appUrl(STUDENT_BASE_URL, '/register'))
  await studentPage.waitForLoadState('domcontentloaded')
  await studentPage.screenshot({ path: join(screenshotsDir, '1_student_register.png') })

  await studentPage.getByLabel('Имя').fill('Григорий Тестировщик')
  await studentPage.getByLabel('Email').fill(studentEmail)
  await studentPage.getByLabel('Пароль').fill(password)
  await studentPage.screenshot({ path: join(screenshotsDir, '2_student_register_filled.png') })
  await studentPage.getByRole('button', { name: 'Создать аккаунт' }).click()

  // Dashboard
  await expect(studentPage).toHaveURL(/\/app$/)
  await studentPage.screenshot({ path: join(screenshotsDir, '3_student_dashboard.png') })

  // Course Page
  await studentPage.goto(appUrl(STUDENT_BASE_URL, '/app/course'))
  await studentPage.screenshot({ path: join(screenshotsDir, '4_student_course.png') })

  // Exams Page
  await studentPage.goto(appUrl(STUDENT_BASE_URL, '/app/exams'))
  await studentPage.screenshot({ path: join(screenshotsDir, '5_student_exams.png') })

  // Start Exam
  const e2eCard = studentPage.locator('.card').filter({ hasText: 'E2E UI Theme' })
  await expect(e2eCard.first()).toBeVisible()
  await e2eCard.first().getByRole('button', { name: 'Начать' }).click()

  // Exam session
  await expect(studentPage).toHaveURL(/\/app\/exams\//)
  await studentPage.screenshot({ path: join(screenshotsDir, '6_student_exam_session.png') })

  // Answer question
  await expect(studentPage.getByText('Вопрос')).toBeVisible()
  await studentPage.getByLabel('Ваш ответ').fill('42')
  await studentPage.screenshot({ path: join(screenshotsDir, '7_student_exam_answered.png') })
  await studentPage.getByRole('button', { name: 'Отправить ответ' }).click()

  // Stats Page
  await studentPage.goto(appUrl(STUDENT_BASE_URL, '/app/stats'))
  await studentPage.screenshot({ path: join(screenshotsDir, '8_student_stats.png') })

  // Profile Page
  await studentPage.goto(appUrl(STUDENT_BASE_URL, '/app/profile'))
  await studentPage.screenshot({ path: join(screenshotsDir, '9_student_profile.png') })
  
  await studentContext.close()


  // 2. --- ADMIN PANEL ---
  console.log('Testing Admin Panel...')
  const adminContext = await browser.newContext({
    viewport: { width: 1280, height: 800 }
  })
  const adminPage = await adminContext.newPage()

  // Capture console and errors
  adminPage.on('console', msg => console.log('ADMIN CONSOLE:', msg.type(), msg.text()))
  adminPage.on('pageerror', err => console.log('ADMIN PAGE ERROR:', err.message))

  await adminPage.goto(appUrl(ADMIN_BASE_URL, '/login'))
  await adminPage.waitForLoadState('domcontentloaded')
  
  // Wait a bit to let React render
  await adminPage.waitForTimeout(3000)
  await adminPage.screenshot({ path: join(screenshotsDir, '10_admin_login.png') })

  // Login
  await adminPage.getByLabel('Email').fill('admin@example.com')
  await adminPage.getByLabel('Пароль').fill('Admin123!')
  await adminPage.screenshot({ path: join(screenshotsDir, '11_admin_login_filled.png') })
  await adminPage.getByRole('button', { name: 'Войти' }).click()

  // Dashboard
  await expect(adminPage).toHaveURL(/\/dashboard$/)
  await adminPage.screenshot({ path: join(screenshotsDir, '12_admin_dashboard.png') })

  // Knowledge base / Documents
  await adminPage.goto(appUrl(ADMIN_BASE_URL, '/knowledge-base'))
  await adminPage.screenshot({ path: join(screenshotsDir, '13_admin_knowledge_base.png') })

  // Questions management
  await adminPage.goto(appUrl(ADMIN_BASE_URL, '/questions'))
  await adminPage.screenshot({ path: join(screenshotsDir, '14_admin_questions.png') })

  await adminContext.close()
  console.log('All tests completed and screenshots saved!')
})
