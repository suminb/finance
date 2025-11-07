# Jets - Flight Data for Airline Financial Prediction

## Project Overview

This project explores using alternative data (flight tracking information) to predict or correlate with the financial performance of airline companies. Rather than relying solely on traditional financial metrics and quarterly reports, we aim to gather real-time operational data that may provide leading indicators of airline revenue and performance.

## Core Hypothesis

**Flight volume and operational metrics are directly correlated with airline financial performance and may provide early signals before quarterly earnings are released.**

### Key Relationships
- More flights → More capacity → More potential revenue
- High load factors → Strong demand → Better margins
- Cancellations/delays → Operational issues → Potential negative impact
- Route expansion → Growth strategy → Future revenue potential

## Rationale

### Why This Approach Makes Sense

1. **Direct Relationship**: Flight data has a clear, logical connection to airline revenue
   - Number of flights = Available Seat Miles (ASM)
   - Passengers × distance = Revenue Passenger Miles (RPM)
   - Load factor = RPM / ASM = Revenue efficiency

2. **Real-time Signal**: Flight data is available immediately, while earnings are reported quarterly with a lag

3. **Publicly Available**: Flight tracking data is legal and publicly accessible (not insider information)

4. **Proven Method**: Institutional investors and hedge funds actively use alternative data sources like this

5. **Tractable Scope**: More focused and manageable than broad sentiment analysis or general news scraping

### Realistic Expectations

**Limitations:**
- Major airlines (AAL, DAL, UAL, LUV) are highly efficient markets - data may already be priced in
- Flight volume alone doesn't capture pricing power, fuel costs, labor issues, or other margin drivers
- High seasonality requires sophisticated modeling
- Institutional players already monitor this data with more resources

**Where It Could Work:**
- Smaller regional carriers with less analyst coverage
- Relative performance comparisons (which airline is outperforming)
- Confirming signals from other data sources
- Spotting inflection points in growth/decline trends
- Academic research and learning exercise

## Data Sources

### Free/Open APIs
- **OpenSky Network** - Free for research, crowdsourced ADS-B data
- **ADS-B Exchange** - Community-driven flight tracking
- **FlightAware API** - Limited free tier available
- **FAA ASPM** - Airport System Performance Metrics (delays, cancellations)

### Paid APIs (Future Consideration)
- **FlightStats/Cirium** - Comprehensive commercial data
- **FlightRadar24 API** - Global coverage with historical data
- **OAG** - Flight schedules and status

## Key Metrics to Track

### Primary Metrics
1. **Flight Volume**
   - Total flights per day/week/month
   - Scheduled vs. actual flights
   - Year-over-year growth rates

2. **Available Seat Miles (ASM)**
   - Calculated from: flights × aircraft capacity × distance
   - Measures total capacity offered

3. **Route Analysis**
   - Most active routes
   - New routes added/removed
   - Domestic vs. international split

4. **Operational Performance**
   - Cancellation rates
   - Delay statistics
   - On-time performance

### Secondary Metrics (If Available)
- Load factor estimates
- Average ticket prices (scraped from booking sites)
- Aircraft utilization rates
- Fleet composition changes

## Target Airlines

### Initial Focus (Major US Carriers)
- **AAL** - American Airlines
- **DAL** - Delta Air Lines
- **UAL** - United Airlines
- **LUV** - Southwest Airlines
- **JBLU** - JetBlue Airways
- **ALK** - Alaska Air Group

### Potential Expansion
- Regional carriers (less efficient markets)
- International carriers serving US routes
- Cargo airlines (FDX, UPS)

## Technical Architecture

### Data Collection
- Scheduled data ingestion (hourly/daily)
- Flight tracking API integration
- Data normalization and cleaning
- Time series database storage

### Analysis Pipeline
1. **Data Aggregation**: Roll up individual flights to daily/weekly metrics
2. **Seasonality Adjustment**: Account for holidays, summer travel, etc.
3. **Comparison to Historical**: YoY growth, trends, anomalies
4. **Correlation Analysis**: Compare to stock prices and earnings
5. **Feature Engineering**: Create derived metrics and signals

### Storage & Infrastructure
- Time series database (InfluxDB, TimescaleDB, or similar)
- Scheduled jobs (cron, Airflow, or similar)
- API rate limiting and error handling
- Historical data backfill

## Success Metrics

### Phase 1: Data Collection & Validation
- Successfully collect flight data for 3-6 months
- Verify data quality and completeness
- Calculate key metrics (ASM, growth rates, etc.)

### Phase 2: Correlation Analysis
- Compare historical flight data to actual earnings
- Measure correlation strength (Pearson, Spearman)
- Identify lead/lag relationships
- Test statistical significance

### Phase 3: Predictive Modeling (Optional)
- Build simple models using flight data
- Backtest against historical earnings
- Compare to analyst estimates
- Risk-adjusted returns analysis

## Risks & Challenges

1. **Market Efficiency**: Large cap airlines are highly liquid with extensive analyst coverage
2. **Incomplete Picture**: Flight volume is only one component of financial performance
3. **Data Quality**: Free APIs may have gaps, delays, or errors
4. **Seasonality**: Strong seasonal patterns require careful modeling
5. **Rate Limits**: Free API tiers may limit data collection frequency
6. **Storage Costs**: Flight data accumulates quickly
7. **Regulatory**: Ensure compliance with API terms of service

## Alternative Enhancements

To improve predictive power, consider combining with:
- **Fuel prices**: Major cost driver for airlines
- **Consumer spending data**: Indicates travel demand
- **Hotel/rental car bookings**: Correlated travel indicators
- **Economic indicators**: Employment, GDP, consumer confidence
- **Social media sentiment**: Brand perception and customer satisfaction
- **Weather patterns**: Impact on cancellations and operations

## Learning Outcomes

Even if this doesn't generate alpha, valuable skills gained:
- Working with real-time APIs
- Time series data engineering
- Alternative data analysis
- Feature engineering for financial modeling
- Understanding market efficiency in practice
- Data pipeline architecture

## Getting Started

### Phase 1: Proof of Concept
1. Choose one free API (recommend OpenSky Network)
2. Collect 1 week of flight data for 2-3 major airlines
3. Calculate basic metrics (flight counts, growth rates)
4. Visualize the data
5. Compare to recent stock price movements (qualitative)

### Phase 2: Historical Analysis
1. Obtain historical flight data (if available)
2. Align with historical earnings dates
3. Calculate correlations
4. Identify any leading indicators

### Phase 3: Production System
1. Set up automated data collection
2. Build monitoring and alerting
3. Create dashboard for tracking metrics
4. Implement backtesting framework

## Next Steps

- [ ] Research API options and sign up for access
- [ ] Design database schema for flight data
- [ ] Create data collection script
- [ ] Set up development environment
- [ ] Define exact metrics to track
- [ ] Plan data visualization approach

## References & Resources

- [Alternative Data in Finance](https://en.wikipedia.org/wiki/Alternative_data_(finance))
- [OpenSky Network API Documentation](https://openskynetwork.github.io/opensky-api/)
- [FlightAware API Documentation](https://www.flightaware.com/commercial/flightxml/)
- [FAA Aviation System Performance Metrics](https://aspm.faa.gov/)
- Academic papers on alternative data and flight tracking

---

**Project Status**: Planning / Documentation Phase  
**Created**: November 7, 2025  
**Last Updated**: November 7, 2025

