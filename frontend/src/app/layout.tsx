import './globals.css'

export const metadata = {
  title: 'Review Gap Analyzer',
  description: 'Analyze app store reviews to identify user pain points',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}