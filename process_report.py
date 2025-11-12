"""
Report processing logic extracted for dashboard use
FIXED: High Growth filter now correctly identifies clients with Previous <= $5K AND Current >= $50K
"""

import pandas as pd
from datetime import datetime


def process_growth_report(df_24m, df_12m, output_file):
    """
    Process growth report from 24-month and 12-month data
    
    Args:
        df_24m: DataFrame with 24-month data
        df_12m: DataFrame with 12-month data
        output_file: Path to output Excel file
    
    Returns:
        dict: Report statistics
    """
    
    # Configuration
    INR_TO_USD = 84
    
    # Prepare 24-month data
    df_24m_prep = df_24m[[
        'CorporateID', 'CorporateName', 'UserName', 'TotalNR1'
    ]].copy()
    df_24m_prep.columns = [
        'CorporateID', 'CorporateName_prev', 'UserName_prev', '24_Month_Revenue'
    ]
    
    # Prepare 12-month data
    # Check if URL column exists in the source data
    columns_to_extract = ['CorporateID', 'CorporateName', 'UserName', 'TotalNR1']
    if 'URL' in df_12m.columns:
        columns_to_extract.append('URL')
        print("[INFO] URL column found in source data")
    else:
        print("[INFO] URL column not found in source data - will generate URLs from CorporateID")
    
    df_12m_prep = df_12m[columns_to_extract].copy()
    
    new_column_names = ['CorporateID', 'CorporateName_curr', 'UserName_curr', '12_Month_Revenue']
    if 'URL' in df_12m.columns:
        new_column_names.append('URL_curr')
    
    df_12m_prep.columns = new_column_names
    
    # Merge datasets
    merged = pd.merge(df_24m_prep, df_12m_prep, on='CorporateID', how='outer')
    
    # Fill missing values
    merged['24_Month_Revenue'].fillna(0, inplace=True)
    merged['12_Month_Revenue'].fillna(0, inplace=True)
    
    # Calculate Previous 12M Revenue
    merged['Previous_12M_Revenue'] = merged['24_Month_Revenue'] - merged['12_Month_Revenue']
    
    # Convert to USD
    merged['Previous_12M_USD'] = merged['Previous_12M_Revenue'] / INR_TO_USD
    merged['Current_12M_USD'] = merged['12_Month_Revenue'] / INR_TO_USD
    
    # Identify exceptions (negative values)
    exceptions = merged[
        (merged['Previous_12M_USD'] < 0) | 
        (merged['Current_12M_USD'] < 0)
    ].copy()
    
    # Clean data (remove exceptions)
    merged_clean = merged[
        (merged['Previous_12M_USD'] >= 0) & 
        (merged['Current_12M_USD'] >= 0)
    ].copy()
    
    # Calculate growth metrics
    merged_clean['Growth_USD'] = merged_clean['Current_12M_USD'] - merged_clean['Previous_12M_USD']
    
    # Handle division by zero for growth percentage
    merged_clean['Growth_%'] = merged_clean.apply(
        lambda row: (row['Growth_USD'] / row['Previous_12M_USD'] * 100) 
        if row['Previous_12M_USD'] != 0 else 0, 
        axis=1
    )
    
    # Populate UserName (prioritize current, fallback to previous)
    merged_clean['UserName'] = merged_clean['UserName_curr'].fillna(
        merged_clean['UserName_prev']
    )
    
    # Round USD values to whole numbers (no decimals) and convert to int
    merged_clean['Previous_12M_USD'] = merged_clean['Previous_12M_USD'].round(0).astype(int)
    merged_clean['Current_12M_USD'] = merged_clean['Current_12M_USD'].round(0).astype(int)
    merged_clean['Growth_USD'] = merged_clean['Growth_USD'].round(0).astype(int)
    
    # Check if URL column exists, if not create one from CorporateID
    if 'URL_curr' not in merged_clean.columns:
        # Generate URL from CorporateID pattern: https://rms2.koenig-solutions.com/corporate/{CorporateID}
        merged_clean['URL_curr'] = merged_clean['CorporateID'].apply(
            lambda cid: f"https://rms2.koenig-solutions.com/corporate/{cid}" if pd.notna(cid) and str(cid).strip() != '' else ''
        )
        print("[INFO] URL column not found in source data, generated URLs from CorporateID pattern")
    else:
        # URL exists, but fill any blanks with generated URLs
        merged_clean['URL_curr'] = merged_clean.apply(
            lambda row: row['URL_curr'] if pd.notna(row['URL_curr']) and str(row['URL_curr']).strip() != '' 
            else f"https://rms2.koenig-solutions.com/corporate/{row['CorporateID']}" if pd.notna(row['CorporateID']) and str(row['CorporateID']).strip() != '' 
            else '',
            axis=1
        )
        print("[INFO] URL column found, filled missing URLs with generated pattern")
    
    # Select and rename columns for Growth Comparison sheet
    growth_comparison = merged_clean[[
        'CorporateID', 'CorporateName_curr', 'UserName', 'URL_curr',
        'Previous_12M_USD', 'Current_12M_USD', 'Growth_USD', 'Growth_%'
    ]].copy()
    
    growth_comparison.columns = [
        'CorporateID', 'CompanyName', 'UserName', 'URL',
        'Previous_12M_USD', 'Current_12M_USD', 'Growth_USD', 'Growth_%'
    ]
    
    # Sort by Growth_USD descending
    growth_comparison.sort_values('Growth_USD', ascending=False, inplace=True)
    growth_comparison.reset_index(drop=True, inplace=True)
    
    # FIXED: Create High Growth sheet BEFORE any sorting/formatting
    # Filter on raw numeric values from merged_clean
    print("\n[DEBUG] Creating High Growth filter...")
    print(f"Total clean clients: {len(merged_clean)}")
    
    # Apply filter on merged_clean with raw numeric values
    high_growth_mask = (
        (merged_clean['Previous_12M_USD'] <= 5000) & 
        (merged_clean['Current_12M_USD'] >= 50000)
    )
    
    high_growth_data = merged_clean[high_growth_mask].copy()
    
    print(f"[DEBUG] High Growth clients found: {len(high_growth_data)}")
    
    # Create High Growth report from filtered data
    high_growth = pd.DataFrame()
    high_growth['CorporateID'] = high_growth_data['CorporateID']
    high_growth['CompanyName'] = high_growth_data['CorporateName_curr']
    high_growth['UserName'] = high_growth_data['UserName']
    high_growth['URL'] = high_growth_data['URL_curr'] if 'URL_curr' in high_growth_data.columns else ''
    high_growth['Previous_12M_USD'] = high_growth_data['Previous_12M_USD']
    high_growth['Current_12M_USD'] = high_growth_data['Current_12M_USD']
    high_growth['Growth_USD'] = high_growth_data['Growth_USD']
    high_growth['Growth_%'] = high_growth_data['Growth_%']
    
    # Sort High Growth by Growth_% descending
    high_growth.sort_values('Growth_%', ascending=False, inplace=True)
    high_growth.reset_index(drop=True, inplace=True)
    
    # Debug output - show first few high growth clients
    if len(high_growth) > 0:
        print("\n[DEBUG] First 5 High Growth clients:")
        for idx, row in high_growth.head(5).iterrows():
            print(f"  {row['CompanyName']:40s} Prev: ${row['Previous_12M_USD']:>10,.2f}  Curr: ${row['Current_12M_USD']:>10,.2f}")
    
    # Create Summary sheet
    # Get top client (biggest mover by Growth_USD) - FIRST row
    top_client = growth_comparison.iloc[0] if len(growth_comparison) > 0 else None
    
    summary_data = {
        'Metric': [
            '🏆 TOP PERFORMER - BIGGEST MOVER',
            'Company Name',
            'Corporate ID',
            'User Name',
            'Previous 12M Revenue (USD)',
            'Current 12M Revenue (USD)',
            'Growth Amount (USD)',
            'Growth Percentage',
            'Company URL',
            '',  # Empty row for spacing
            '📊 OVERALL STATISTICS',
            'Total Clients Analyzed',
            'High Growth Clients (Prev ≤$5K, Curr ≥$50K)',
            'Average Previous 12M Revenue (USD)',
            'Average Current 12M Revenue (USD)',
            'Total Growth (USD)',
            'Average Growth % (All Clients)',
            'Total Exceptions',
            '',  # Empty row for spacing
            'Report Generated'
        ],
        'Value': [
            '',  # Empty cell next to header
            top_client['CompanyName'] if top_client is not None else 'N/A',
            str(top_client['CorporateID']) if top_client is not None else 'N/A',
            top_client['UserName'] if top_client is not None else 'N/A',
            f"${int(top_client['Previous_12M_USD']):,}" if top_client is not None else 'N/A',
            f"${int(top_client['Current_12M_USD']):,}" if top_client is not None else 'N/A',
            f"${int(top_client['Growth_USD']):,}" if top_client is not None else 'N/A',
            f"{top_client['Growth_%']:.1f}%" if top_client is not None else 'N/A',
            top_client['URL'] if top_client is not None else 'N/A',
            '',  # Empty row
            '',  # Empty cell next to header
            len(growth_comparison),
            len(high_growth),
            f"${int(growth_comparison['Previous_12M_USD'].mean()):,}",
            f"${int(growth_comparison['Current_12M_USD'].mean()):,}",
            f"${int(growth_comparison['Growth_USD'].sum()):,}",
            f"{growth_comparison['Growth_%'].mean():.1f}%",
            len(exceptions),
            '',  # Empty row
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ]
    }
    summary = pd.DataFrame(summary_data)
    
    # Prepare Exceptions sheet
    if len(exceptions) > 0:
        exceptions_output = exceptions[[
            'CorporateID', 'CorporateName_curr',
            'Previous_12M_USD', 'Current_12M_USD'
        ]].copy()
        exceptions_output.columns = [
            'CorporateID', 'CompanyName',
            'Previous_12M_USD', 'Current_12M_USD'
        ]
    else:
        exceptions_output = pd.DataFrame(columns=[
            'CorporateID', 'CompanyName',
            'Previous_12M_USD', 'Current_12M_USD'
        ])
    
    # Write to Excel with multiple sheets
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        growth_comparison.to_excel(writer, sheet_name='Growth Comparison', index=False)
        high_growth.to_excel(writer, sheet_name='High Growth 5K-50K USD', index=False)
        summary.to_excel(writer, sheet_name='Summary', index=False)
        exceptions_output.to_excel(writer, sheet_name='Exceptions', index=False)
        
        # Format Summary sheet to highlight top performer
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        
        workbook = writer.book
        summary_sheet = workbook['Summary']
        
        # Make column A wider for metric names
        summary_sheet.column_dimensions['A'].width = 40
        summary_sheet.column_dimensions['B'].width = 50
        
        # TOP PERFORMER is now at row 2 (after header row 1)
        # Row 1: Header (auto-generated by pandas)
        # Row 2: TOP PERFORMER header
        # Rows 3-10: Top performer details
        
        # Highlight TOP PERFORMER header (row 2)
        for cell in summary_sheet[2]:
            cell.fill = PatternFill(start_color='FFD700', end_color='FFD700', fill_type='solid')
            cell.font = Font(bold=True, size=14, color='000000')
            cell.alignment = Alignment(horizontal='center', vertical='center')
        
        # Highlight top performer details (rows 3-10) with light blue
        for row_idx in range(3, 11):  # Rows 3-10
            for cell in summary_sheet[row_idx]:
                cell.fill = PatternFill(start_color='E3F2FD', end_color='E3F2FD', fill_type='solid')
                cell.font = Font(size=11)
                # Make metric names in column A bold
                if cell.column == 1:
                    cell.font = Font(bold=True, size=11)
        
        # Find and highlight OVERALL STATISTICS header
        for row_idx in range(1, summary_sheet.max_row + 1):
            cell_value = str(summary_sheet.cell(row_idx, 1).value) if summary_sheet.cell(row_idx, 1).value else ''
            if 'OVERALL STATISTICS' in cell_value or '📊' in cell_value:
                # Highlight this header row with light green
                for cell in summary_sheet[row_idx]:
                    cell.fill = PatternFill(start_color='C8E6C9', end_color='C8E6C9', fill_type='solid')
                    cell.font = Font(bold=True, size=12, color='000000')
                    cell.alignment = Alignment(horizontal='center', vertical='center')
                break
    
    print(f"\n[SUCCESS] Report saved to: {output_file}")
    print(f"  - Growth Comparison: {len(growth_comparison)} clients")
    print(f"  - High Growth: {len(high_growth)} clients")
    print(f"  - Exceptions: {len(exceptions)} clients")
    if top_client is not None:
        print(f"\n[TOP PERFORMER] {top_client['CompanyName']}")
        print(f"  - Growth: ${top_client['Growth_USD']:,.0f} ({top_client['Growth_%']:.1f}%)")
        print(f"  - From: ${top_client['Previous_12M_USD']:,.0f} to ${top_client['Current_12M_USD']:,.0f}")
    
    # Return statistics
    return {
        'total_clients': len(growth_comparison),
        'high_growth_clients': len(high_growth),
        'exceptions': len(exceptions),
        'total_growth_usd': growth_comparison['Growth_USD'].sum(),
        'avg_growth_pct': growth_comparison['Growth_%'].mean(),
        'top_performer': top_client['CompanyName'] if top_client is not None else 'N/A',
        'top_performer_growth': top_client['Growth_USD'] if top_client is not None else 0
    }
