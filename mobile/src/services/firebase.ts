import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import { Platform } from 'react-native';
import { tokenApi } from './api';

Notifications.setNotificationHandler({
  handleNotification: async () => ({
    shouldShowAlert: true,
    shouldPlaySound: false,
    shouldSetBadge: false,
  }),
});

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  let token: string | null = null;

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync('default', {
      name: 'default',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: '#6366f1',
    });
  }

  if (Device.isDevice) {
    const { status: existingStatus } = await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;
    if (existingStatus !== 'granted') {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }
    if (finalStatus !== 'granted') {
      alert('Không thể lấy quyền thông báo!');
      return null;
    }
    const tokenData = await Notifications.getExpoPushTokenAsync({
      projectId: 'your-project-id',
    });
    token = tokenData.data;
  } else {
    alert('Phải sử dụng thiết bị vật lý để nhận thông báo đẩy');
  }

  return token;
}

export async function setupNotifications(): Promise<string | null> {
  const expoPushToken = await registerForPushNotificationsAsync();
  if (expoPushToken) {
    try {
      await tokenApi.registerFcmToken(expoPushToken);
    } catch (e) {
      console.log('FCM token register error:', e);
    }
  }
  return expoPushToken;
}
