// Service Worker cho Firebase Cloud Messaging
// Project: datn-2905
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js')

firebase.initializeApp({
  apiKey: 'AIzaSyBCc4US7XyQW4Nm5tmQzu_N8v7ZeYZnmfs',
  authDomain: 'datn-2905.firebaseapp.com',
  projectId: 'datn-2905',
  storageBucket: 'datn-2905.firebasestorage.app',
  messagingSenderId: '188981294715',
  appId: '1:188981294715:web:748151390df5b66947d4de',
  measurementId: 'G-LWXSBBSEQ1'
})

const messaging = firebase.messaging()

// Xử lý thông báo khi app ở background
messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] Received background message ', payload)

  const notificationTitle = payload.notification?.title || 'Thông báo mới'
  const notificationOptions = {
    body: payload.notification?.body || '',
    icon: payload.notification?.icon || '/logos/fpt.png',
    badge: '/logos/fpt.png',
    data: payload.data || {},
    tag: payload.data?.key || 'notification',
    renotify: true,
    vibrate: [200, 100, 200]
  }

  self.registration.showNotification(notificationTitle, notificationOptions)
})

// Xử lý khi user click vào notification
self.addEventListener('notificationclick', (event) => {
  event.notification.close()

  const urlToOpen = event.notification.data?.url || '/'
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clientList) => {
      for (const client of clientList) {
        if (client.url.includes(urlToOpen) && 'focus' in client) {
          return client.focus()
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen)
      }
    })
  )
})