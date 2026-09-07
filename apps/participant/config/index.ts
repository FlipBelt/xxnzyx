import { defineConfig } from '@tarojs/cli'

const apiBase = process.env.TARO_APP_API_BASE || 'http://127.0.0.1:8100/api/v1'
const outputRoot = process.env.TARO_ENV === 'h5' ? 'dist/h5' : 'dist/weapp'
const publicPath = process.env.TARO_PUBLIC_PATH || '/flipbelt/'

export default defineConfig({
  projectName: 'flipbelt-40s-challenge',
  date: '2026-08-19',
  designWidth: 750,
  deviceRatio: {
    640: 2.34 / 2,
    750: 1,
    828: 1.81 / 2
  },
  sourceRoot: 'src',
  outputRoot,
  framework: 'vue3',
  compiler: 'webpack5',
  defineConstants: {
    __FLIPBELT_API_BASE__: JSON.stringify(apiBase)
  },
  mini: {},
  h5: {
    publicPath,
    router: { mode: 'hash' },
    // 发布后让入口与分包都带内容哈希，避免手机浏览器继续使用同名旧分包。
    webpackChain(chain) {
      chain.output.filename('js/[name].[contenthash:8].js')
      chain.output.chunkFilename('chunk/[name].[contenthash:8].js')
    },
    // CSS 也使用内容哈希，避免长期缓存掩盖移动端视觉调整。
    miniCssExtractPluginOption: {
      filename: 'css/[name].[contenthash:8].css',
      chunkFilename: 'css/[name].[contenthash:8].css'
    }
  }
})
