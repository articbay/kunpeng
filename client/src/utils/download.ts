const MOSCOW_TIME_ZONE = 'Europe/Moscow'

export function moscowTimestamp(date = new Date()): string {
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: MOSCOW_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).formatToParts(date)
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}${values.month}${values.day}_${values.hour}${values.minute}${values.second}`
}

export function downloadExcel(blob: Blob, businessName: string): void {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${businessName}_${moscowTimestamp()}.xlsx`
  document.body.appendChild(link)
  link.click()
  link.remove()

  // Give the browser time to consume the Blob before releasing its object URL.
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
