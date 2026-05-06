/**
 * Unit tests for file_to_name.ts
 */
import { typeToPathMap } from '../../utils/file_to_name'

describe('file_to_name', () => {
  describe('typeToPathMap', () => {
    it('should contain common icon types', () => {
      expect(typeToPathMap.user).toBe('user')
      expect(typeToPathMap.home).toBe('home')
      expect(typeToPathMap.search).toBe('search')
      expect(typeToPathMap.gear).toBe('gear')
    })

    it('should map icon types to file paths', () => {
      expect(typeToPathMap.accessibility).toBe('accessibility')
      expect(typeToPathMap.document).toBe('document')
      expect(typeToPathMap.folderClosed).toBe('folder_closed')
    })

    it('should handle token icon types', () => {
      expect(typeToPathMap.tokenString).toBe('tokenString')
      expect(typeToPathMap.tokenNumber).toBe('tokenNumber')
      expect(typeToPathMap.tokenBoolean).toBe('tokenBoolean')
    })
  })
})

