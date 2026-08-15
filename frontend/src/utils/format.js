export const PLATFORM_LOGOS = {
  'FPT Shop': './logos/fpt.jpg',
  'Thế Giới Di Động': './logos/tgdd.jpg',
  'Điện Máy Xanh': './logos/dmx.jpg',
  'CellphoneS': './logos/cellphones.png',
  'Hoàng Hà Mobile': './logos/hoangha.svg',
  'Di Động Việt': './logos/didongviet.svg',
  'Viettel Store': './logos/viettelstore.png',
  'Clickbuy': './logos/clickbuy.png',
  'MobileCity': './logos/mobilecity.webp',
  // Fallback cũ
  FPT: './logos/fpt.jpg',
  TGDD: './logos/tgdd.jpg',
  DMX: './logos/dmx.jpg'
}

export function formatPrice(value) {
  if (value === null || value === undefined || isNaN(value)) return '--'
  return Number(value).toLocaleString('vi-VN') + 'đ'
}

export function formatDate(dateString) {
  if (!dateString || typeof dateString !== 'string') return '--/--/----'
  if (/^\d{2}\/\d{2}\/\d{4}$/.test(dateString)) return dateString
  const parts = dateString.split('-')
  if (parts.length === 3) return `${parts[2]}/${parts[1]}/${parts[0]}`
  return dateString
}

export function getRandomComments(commentsArray, maxLimit = 10) {
  if (!commentsArray || commentsArray.length === 0) return []
  const shuffled = [...commentsArray].sort(() => 0.5 - Math.random())
  return shuffled.slice(0, maxLimit)
}

export function fillMissingDates(labels, data) {
  if (!labels || labels.length === 0) return { labels, data }

  const resultLabels = []
  const resultData = []

  let startDate, endDate
  try {
    const firstParts = labels[0].split('/')
    const lastParts = labels[labels.length - 1].split('/')
    startDate = new Date(2026, parseInt(firstParts[1]) - 1, parseInt(firstParts[0]))
    endDate = new Date(2026, parseInt(lastParts[1]) - 1, parseInt(lastParts[0]))
  } catch (e) {
    return { labels, data }
  }

  const priceMap = {}
  labels.forEach((label, idx) => {
    priceMap[label] = data[idx] || data[data.length - 1]
  })

  const currentDate = new Date(startDate)
  while (currentDate <= endDate) {
    const day = String(currentDate.getDate()).padStart(2, '0')
    const month = String(currentDate.getMonth() + 1).padStart(2, '0')
    const label = `${day}/${month}`

    resultLabels.push(label)
    resultData.push(priceMap[label] || resultData[resultData.length - 1] || data[0])

    currentDate.setDate(currentDate.getDate() + 1)
  }

  if (resultLabels.length > 7) {
    return {
      labels: resultLabels.slice(-7),
      data: resultData.slice(-7)
    }
  }

  return { labels: resultLabels, data: resultData }
}

export const PQS_COLORS = {
  green: '#22c55e',
  yellow: '#eab308',
  orange: '#f97316',
  red: '#ef4444'
}

export const REC_COLORS = {
  green: 'rec-green',
  yellow: 'rec-yellow',
  orange: 'rec-orange',
  red: 'rec-red'
}

export const SENTIMENT_CONFIG = {
  POSITIVE: { cls: 'cmt-pos', badge: 'badge-pos', label: 'TÍCH CỰC' },
  NEGATIVE: { cls: 'cmt-neg', badge: 'badge-neg', label: 'TIÊU CỰC' },
  NEUTRAL: { cls: 'cmt-neu', badge: 'badge-neu', label: 'TRUNG TÍNH' }
}

export function getRqsColor(rqs) {
  if (rqs >= 4) return '#16a34a'
  if (rqs >= 3) return '#ca8a04'
  return '#dc2626'
}