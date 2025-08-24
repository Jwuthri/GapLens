# Review Gap Analyzer Frontend

A Next.js frontend application for analyzing app store reviews and website feedback to identify user pain points and product opportunities.

## Features

- **Dual Analysis Types**: Support for both app store analysis (Google Play/App Store) and website review analysis
- **Interactive Dashboard**: View complaint clusters with summary statistics and visualizations
- **Real-time Updates**: Live status polling during analysis processing
- **Export Functionality**: Export results in CSV or JSON format
- **Responsive Design**: Works on desktop and mobile devices
- **Error Handling**: Comprehensive error boundaries and user feedback

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment configuration:
```bash
cp .env.local.example .env.local
```

3. Update the API URL in `.env.local` if needed:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

Run the development server:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production

```bash
npm run build
npm start
```

## Project Structure

```
src/
├── app/                 # Next.js app router pages
├── components/          # React components
│   ├── AnalysisForm.tsx        # Main input form
│   ├── ResultsDashboard.tsx    # Results display
│   ├── SummaryStats.tsx        # Statistics cards
│   ├── ClustersList.tsx        # Complaint clusters list
│   ├── ClustersChart.tsx       # Chart visualization
│   ├── ClusterDetailModal.tsx  # Detailed cluster view
│   ├── LoadingState.tsx        # Loading indicators
│   └── ErrorBoundary.tsx       # Error handling
├── services/            # API integration
├── types/              # TypeScript type definitions
└── utils/              # Utility functions
```

## API Integration

The frontend communicates with the FastAPI backend through:

- `POST /api/v1/analyze` - Submit analysis requests
- `GET /api/v1/analysis/{id}` - Get analysis results
- `GET /api/v1/analysis/{id}/status` - Check processing status
- `GET /api/v1/analysis/{id}/export` - Export results

## Technologies Used

- **Next.js 14** - React framework with app router
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Chart.js** - Data visualization
- **Lucide React** - Icons
- **React Chart.js 2** - Chart components