/**
 * Unit tests for index page
 */
import React from 'react'
import { render, screen } from '@testing-library/react'
import HomePage from '../../pages/index'

// Mock MainPageContent
jest.mock('../../components/mainPage/content', () => ({
  MainPageContent: () => <div data-testid="main-content">Main Content</div>
}))

// Mock PageTemplate
jest.mock('../../components/pageTemplate', () => ({
  __esModule: true,
  default: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="page-template">{children}</div>
  )
}))

describe('HomePage', () => {
  it('should render home page', () => {
    render(<HomePage />)
    expect(screen.getByTestId('main-content')).toBeInTheDocument()
    expect(screen.getByTestId('page-template')).toBeInTheDocument()
  })

  it('should create performance marks', () => {
    const markSpy = jest.spyOn(window.performance, 'mark')
    render(<HomePage />)
    
    // Should create performance marks
    expect(markSpy).toHaveBeenCalled()
  })
})


