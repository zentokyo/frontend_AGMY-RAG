import { spawn } from 'node:child_process'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const rootDir = resolve(__dirname, '..')

function runCommand(command, args, cwd) {
  return new Promise((resolvePromise, rejectPromise) => {
    console.log(`\n🚀 Запуск: ${command} ${args.join(' ')}`);
    const child = spawn(command, args, {
      cwd,
      shell: true,
      stdio: 'inherit'
    })

    child.on('close', (code) => {
      if (code === 0) {
        resolvePromise()
      } else {
        rejectPromise(new Error(`Команда "${command} ${args.join(' ')}" завершилась с кодом ${code}`))
      }
    })
  })
}

async function main() {
  try {
    // 1. Сборка статики фронтенда
    await runCommand('npm', ['run', 'build'], rootDir)

    // 2. Пересборка backend контейнеров в Docker
    await runCommand('docker', [
      'compose',
      '--profile',
      'dev',
      'up',
      '-d',
      '--build',
      'assistant_backend',
      'assistant_ingest_worker'
    ], rootDir)

    console.log('\n✅ Проект успешно пересобран!');
  } catch (error) {
    console.error(`\n❌ Ошибка во время пересборки: ${error.message}`);
    process.exit(1)
  }
}

main()
