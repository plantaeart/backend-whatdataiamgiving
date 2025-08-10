# WhatDataIAmGiving API

A FastAPI service for finding and analyzing Terms & Conditions pages using AI with **strict privacy scoring**.

## 🔒 Privacy Scoring System

Our AI analysis uses **strict privacy protection standards**:

### **Privacy Score (0-100)**

- **90-100**: Excellent privacy protection (no external sharing, short retention, strong user control)
- **70-89**: Good privacy protection (minimal sharing, reasonable retention, good user rights)
- **50-69**: Moderate privacy protection (some concerning practices, average user control)
- **30-49**: Poor privacy protection (third-party sharing, long retention, weak user rights)
- **0-29**: Very poor privacy protection (extensive sharing/selling, indefinite retention, no user control)

### **Automatic Score Penalties**

- **Data selling or extensive third-party sharing**: -40 to -65 points
- **External analytics/advertising sharing**: -30 to -45 points
- **Sharing with "business partners"**: -25 to -35 points
- **Indefinite or unclear data retention**: -20 to -30 points
- **Data kept longer than 2 years**: -15 to -25 points
- **Poor user deletion/control options**: -15 to -25 points

### **What Gets Good Scores**

- ✅ **Internal analytics only** (no external sharing)
- ✅ **Short retention periods** (30 days - 1 year)
- ✅ **Easy user data deletion** and export rights
- ✅ **Data used only for core service** functionality

### **What Gets Bad Scores**

- ❌ **ANY external data sharing** (including Google Analytics)
- ❌ **Data selling or advertising partnerships**
- ❌ **Long or indefinite data retention**
- ❌ **Difficult or impossible user data deletion**

## 🚀 Endpoints

### 1. **Find Terms & Conditions**

**`POST /api/find-terms`**

Scan a website to locate Terms & Conditions pages.

```bash
curl -X POST "http://localhost:8001/api/find-terms" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Response:**

```json
{
  "url": "https://example.com",
  "has_terms": true,
  "found_terms_pages": [
    "https://example.com/privacy-policy",
    "https://example.com/terms-of-service"
  ]
}
```

### 2. **AI Analysis**

**`POST /api/analyze-terms`**

Analyze Terms & Conditions using AI (requires Gemini API key).

```bash
curl -X POST "http://localhost:8001/api/analyze-terms" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Response:**

```json
{
  "url": "https://example.com",
  "terms_urls": ["https://example.com/privacy-policy"],
  "analysis": {
    "privacy_score": 35,
    "score_explanation": "Poor privacy protection due to extensive third-party data sharing and long retention periods",
    "terms_analysis": {
      "ok": ["Data encryption in transit", "User account deletion option"],
      "neutral": ["Standard GDPR compliance"],
      "bad": [
        "Shares data with advertising networks",
        "Data retained indefinitely",
        "Extensive third-party partnerships",
        "Vague business partner data sharing"
      ]
    },
    "data_selling": "Shares user data with advertising partners and analytics companies for targeted advertising",
    "data_buyers": [
      "Google Analytics",
      "Facebook advertising network",
      "Marketing automation companies",
      "Business partners (unspecified)"
    ],
    "data_storage": "Cloud storage with indefinite retention. No clear data deletion timeline provided.",
    "main_concerns": [
      "Extensive third-party data sharing",
      "Indefinite data retention",
      "Lack of granular user control"
    ],
    "user_rights": "Users can request account deletion but data may remain with third parties",
    "summary": "Poor privacy practices with extensive data sharing and indefinite retention. Users have limited control over their data once shared with third parties."
  },
  "analysis_method": "url",
  "raw_analysis": null
}
```

## ⚙️ Setup

1. **Install dependencies:**

```bash
uv install
```

2. **Set up environment variables:**

```bash
cp .env.example .env.dev
# Add your Gemini API key to .env.dev
```

3. **Run the server:**

```bash
python -m uvicorn main:app --reload --port 8001
```

4. **View docs:**
   Open http://localhost:8001/docs

## 🔑 API Key Setup

Get a free Gemini API key at: https://ai.google.dev/

Add to `.env.dev`:

```env
GEMINI_API_KEY=your_api_key_here
```

## 💰 Cost Optimization

- **`/find-terms`**: No AI costs, just web scraping
- **`/analyze-terms`**: Only calls AI if terms pages are found
- **Free tier**: 15 requests/minute with Gemini 2.0 Flash
- **Automatic fallback**: URL analysis → Text extraction if needed

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Scraper   │───▶│   Terms Finder   │───▶│   AI Analyzer   │
│                 │    │                  │    │                 │
│ BeautifulSoup + │    │ Pattern Matching │    │ Google Gemini   │
│ HTTPX           │    │ + Link Following │    │ 2.0 Flash       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🎯 Real-World Scores

Based on our strict privacy criteria, typical scores are:

- **Privacy-focused services**: 70-95 points
- **Standard websites with analytics**: 40-60 points
- **Social media platforms**: 15-35 points
- **Ad-supported services**: 10-30 points
- **Data brokers**: 0-15 points

_Note: ANY external data sharing significantly reduces privacy scores_
