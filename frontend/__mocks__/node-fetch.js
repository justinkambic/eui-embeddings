// Mock node-fetch to avoid ESM import issues in Jest
module.exports = jest.fn((url, options) => {
  return Promise.resolve({
    ok: true,
    status: 200,
    json: async () => ({}),
    text: async () => '',
    headers: new Headers(),
  })
})

module.exports.default = module.exports


