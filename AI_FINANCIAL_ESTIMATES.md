# AI-Powered Financial Estimates Feature (SGD)

## Overview
When you click "Connect Singpass", the system now uses OpenAI to generate realistic financial estimates **in Singapore Dollars (SGD)** based on your LinkedIn profile data.

## How It Works

### 1. Profile Data Collection
When you click "Connect Singpass", the system collects your profile information:
- **Name**: From LinkedIn
- **Current Role**: e.g., "Product Lead", "Data Scientist"
- **Years of Experience**: Calculated from job history
- **Location**: e.g., "Singapore"
- **Age**: From profile

### 2. AI-Powered Financial Generation
The system sends your profile to OpenAI GPT-4 with a prompt like:

```
Based on this professional profile, generate realistic financial estimates in SGD:

Profile:
- Name: Yun Bin Choh
- Role: Product Lead
- Years of Experience: 3
- Location: Singapore
- Age: 31

Generate believable financial ranges considering:
- Market rates for Product Lead in Singapore (in SGD)
- Cost of living in Singapore (in SGD)
- Typical savings for someone with 3 years experience (in SGD)
- Common debt levels for someone age 31 (in SGD)
```

### 3. Generated Financial Data
OpenAI returns realistic estimates in **Singapore Dollars (SGD)**:

| Field | Description | Example Range (SGD) |
|-------|-------------|---------------------|
| **Monthly Income** | Salary based on role & experience | $8,000 - $20,000 |
| **Monthly Expenses** | Living costs in Singapore | $4,000 - $7,000 |
| **Liquid Savings** | Cash reserves | $30,000 - $120,000 |
| **Debt** | Loans, credit cards | $0 - $20,000 |
| **Expected Side Income** | Freelance/consulting potential | $800 - $3,000 |

### 4. Smart Estimation Logic

The AI considers:

**Role-Based Income:**
- Junior roles (0-2 yrs): Lower range
- Mid-level (3-5 yrs): Middle range
- Senior (6-10 yrs): Upper range
- Lead/Director (10+ yrs): Premium range

**Location-Based Costs:**
- Singapore: High cost of living
- US (SF, NY): Very high
- Southeast Asia: Moderate to low

**Experience-Based Savings:**
- Early career: Lower savings (3-6 months runway)
- Mid career: Moderate savings (6-12 months)
- Senior: Higher savings (12-24 months)

## Example Generations (in SGD)

### Product Lead, 3 Years, Singapore, Age 31
```json
{
  "monthly_income_usd": 11500,
  "monthly_expenses_usd": 5000,
  "liquid_savings_usd": 45000,
  "debt_usd": 8000,
  "expected_side_income_usd": 1500
}
```

**Reasoning:**
- Product Lead in Singapore with 3 years → ~SGD 11,500/month
- Cost of living in Singapore → ~SGD 5,000/month
- 3 years savings → ~SGD 45,000 (about 9 months runway)
- Some debt is normal for age 31 → ~SGD 8,000
- Product skills can generate side income → ~SGD 1,500/month

### Senior Data Scientist, 8 Years, Singapore, Age 35
```json
{
  "monthly_income_usd": 18000,
  "monthly_expenses_usd": 6500,
  "liquid_savings_usd": 120000,
  "debt_usd": 10000,
  "expected_side_income_usd": 3000
}
```

**Reasoning:**
- Senior DS in Singapore with 8 years → ~SGD 18,000/month (~SGD 216k/year)
- Higher cost of living for senior lifestyle → ~SGD 6,500/month
- 8 years of good income → ~SGD 120,000 saved
- Some debt normal → ~SGD 10,000
- Senior DS consulting potential → ~SGD 3,000/month

## Fallback Behavior

If OpenAI API is unavailable:
- Uses sensible default values
- Typical mid-level professional in Singapore
- Still functional, just not personalized

## Testing the Feature

### 1. Complete LinkedIn Connection First
```
1. Enter LinkedIn URL
2. Click "Connect LinkedIn"
3. Wait for profile to populate
```

### 2. Click Connect Singpass
```
1. Click "Connect Singpass" button
2. Wait 2-3 seconds for AI generation
3. Fields auto-populate with realistic estimates
```

### 3. Check Console Output
In your terminal, you'll see:
```
Generating financial data for profile: Yun Bin Choh, Product Lead
Generated financial data for Yun Bin Choh: {...}
```

## API Key Required

Make sure your `.env` file contains:
```bash
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini
```

## Benefits

✅ **Realistic Estimates**: Based on actual market data and location  
✅ **Time-Saving**: No need to research typical salaries  
✅ **Contextual**: Considers your specific role and experience  
✅ **Smart Defaults**: Falls back gracefully if API unavailable  
✅ **Editable**: You can still manually adjust all values  

## Privacy Note

- Profile data is sent to OpenAI for generation
- No data is stored permanently
- Only used for one-time financial estimation
- You can edit all generated values

## Future Enhancements

- Add confidence scores to estimates
- Show salary range with min/max
- Include industry-specific adjustments
- Add currency conversion for non-USD locations
- Historical salary data integration
- Cost of living API integration

---

**Status**: ✅ Active
**Date**: February 7, 2026
**API**: OpenAI GPT-4o-mini
