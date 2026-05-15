/**
 * Unit tests for icon_renderer.ts
 */
// Mock uuid before importing EUI components to avoid ESM issues
jest.mock('uuid', () => ({
  v4: jest.fn(() => 'mock-uuid'),
  v1: jest.fn(() => 'mock-uuid'),
}))

// Mock react-dom/server before importing icon_renderer
jest.mock('react-dom/server', () => ({
  renderToStaticMarkup: jest.fn(),
}))

jest.mock('fs/promises', () => ({
  mkdir: jest.fn(),
  writeFile: jest.fn(),
}))

import { renderIconToSVG, normalizeSVG, saveSVG } from '../../utils/icon_renderer'
import { renderToStaticMarkup } from 'react-dom/server'
import fs from 'fs/promises'

describe('icon_renderer', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  describe('renderIconToSVG', () => {
    it('should render icon to SVG string', async () => {
      const mockSVG = '<svg viewBox="0 0 24 24"><path d="M0 0 L24 24"/></svg>'
      ;(renderToStaticMarkup as jest.Mock).mockReturnValue(mockSVG)

      const result = await renderIconToSVG('user', 'xl')
      expect(result).toBe(mockSVG)
      expect(renderToStaticMarkup).toHaveBeenCalled()
    })

    it('should return null on error', async () => {
      ;(renderToStaticMarkup as jest.Mock).mockImplementation(() => {
        throw new Error('Render failed')
      })

      const result = await renderIconToSVG('invalid-icon', 'xl')
      expect(result).toBeNull()
    })
  })

  describe('normalizeSVG', () => {
    it('should normalize SVG with viewBox', () => {
      const svg = '<svg viewBox="0 0 24 24"><path d="M0 0"/></svg>'
      const normalized = normalizeSVG(svg, 224)
      expect(normalized).toContain('width="224"')
      expect(normalized).toContain('height="224"')
      expect(normalized).toContain('viewBox="0 0 24 24"')
    })

    it('should normalize SVG with width and height', () => {
      const svg = '<svg width="48" height="48"><path d="M0 0"/></svg>'
      const normalized = normalizeSVG(svg, 224)
      expect(normalized).toContain('width="224"')
      expect(normalized).toContain('height="224"')
    })

    it('should return null for empty SVG', () => {
      const result = normalizeSVG('')
      expect(result).toBeNull()
    })

    it('should use default viewBox when none provided', () => {
      const svg = '<svg><path d="M0 0"/></svg>'
      const normalized = normalizeSVG(svg)
      expect(normalized).toContain('viewBox="0 0 24 24"')
    })
  })

  describe('saveSVG', () => {
    it('should save SVG to file', async () => {
      const mockMkdir = fs.mkdir as jest.Mock
      const mockWriteFile = fs.writeFile as jest.Mock
      mockMkdir.mockResolvedValue(undefined)
      mockWriteFile.mockResolvedValue(undefined)

      const result = await saveSVG('test-icon', '<svg></svg>', './test-output')
      
      expect(mockMkdir).toHaveBeenCalledWith('./test-output', { recursive: true })
      expect(mockWriteFile).toHaveBeenCalled()
      expect(result).toContain('test-icon.svg')
    })

    it('should use default output directory', async () => {
      const mockMkdir = fs.mkdir as jest.Mock
      const mockWriteFile = fs.writeFile as jest.Mock
      mockMkdir.mockResolvedValue(undefined)
      mockWriteFile.mockResolvedValue(undefined)

      await saveSVG('test-icon', '<svg></svg>')
      
      expect(mockMkdir).toHaveBeenCalledWith('./rendered-icons', { recursive: true })
    })
  })
})

