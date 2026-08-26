import { createPinia } from 'pinia'
import { createApp } from 'vue'

import './app.scss'

const app = createApp({})
app.use(createPinia())

export default app
