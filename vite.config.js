import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  define: {
    "__KINESIS_VIDEO_STREAM_INTEGRATION__": false //Set this to true if Kinesis Video Stream Integration is turned on and kinesisVideoStreamIntegration in the frontend function is turned on
  }
})
