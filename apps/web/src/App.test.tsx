import { render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'

import App from './App'

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok: true,
    }),
  )
})

test('renders FluxMed foundation and reports API status', async () => {
  render(<App />)

  expect(
    screen.getByRole('heading', { name: 'FluxMed' }),
  ).toBeInTheDocument()
  expect(await screen.findByText('API online')).toBeInTheDocument()
})
