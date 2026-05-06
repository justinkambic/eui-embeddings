/**
 * Unit tests for PageTemplate component
 */
// Mock uuid before importing EUI components to avoid ESM issues
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'mock-uuid'),
  v1: jest.fn(() => 'mock-uuid'),
}))

import React from 'react'
import { render, screen } from '@testing-library/react'
import PageTemplate from '../../components/pageTemplate'

describe('PageTemplate', () => {
  it('should render page template with header', () => {
    render(
      <PageTemplate>
        <div>Test Content</div>
      </PageTemplate>
    )
    
    expect(screen.getByText('EUI Icon Semantic Search')).toBeInTheDocument()
    expect(screen.getByText('Test Content')).toBeInTheDocument()
  })

  it('should render children content', () => {
    render(
      <PageTemplate>
        <div data-testid="child-content">Child Content</div>
      </PageTemplate>
    )
    
    expect(screen.getByTestId('child-content')).toBeInTheDocument()
  })
})

