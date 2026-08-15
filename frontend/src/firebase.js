import { initializeApp } from 'firebase/app'
import { getMessaging, getToken, onMessage } from 'firebase/messaging'

// ===== FIREBASE CONFIG =====
// Project: datn-2905
const firebaseConfig = {
  apiKey: 'AIzaSyBCc4US7XyQW4Nm5tmQzu_N8v7ZeYZnmfs',
  authDomain: 'datn-2905.firebaseapp.com',
  projectId: 'datn-2905',
  storageBucket: 'datn-2905.firebasestorage.app',
  messagingSenderId: '188981294715',
  appId: '1:188981294715:web:748151390df5b66947d4de',
  measurementId: 'G-LWXSBBSEQ1'
}

// VAPID Key từ Firebase Console → Cloud Messaging → Web Push certificates
// ⚠️ Cần lấy key này từ Firebase Console (Cloud Messaging tab)
export const VAPID_KEY = 'BJxfmABoTXrDw-Rj-sDOZdk7985EOqd8y0w-W8n3dtLc9RsHKVr3pm0HAYkxJW7tsxE4yQQIfLGNI33AdzWk8fo'

const app = initializeApp(firebaseConfig)
export const messaging = getMessaging(app)

// Lấy FCM token cho thiết bị hiện tại
export async function requestFcmToken() {
  try {
    const currentToken = await getToken(messaging, { vapidKey: VAPID_KEY })
    return currentToken
  } catch (err) {
    console.error('Không thể lấy FCM token:', err)
    return null
  }
}

// Lắng nghe thông báo khi app đang mở (foreground)
export function onForegroundMessage(callback) {
  onMessage(messaging, (payload) => {
    callback(payload)
  })
}