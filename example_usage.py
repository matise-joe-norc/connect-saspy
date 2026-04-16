#!/usr/bin/env python3
"""
Example usage of the connect_saspy package.
This demonstrates the typical workflow for using the package.
"""

# Import the package - this will automatically establish a SAS connection
import connect_saspy

def main():
    """Main example function showing typical usage patterns."""
    
    print("Connect SASpy Package Usage Example")
    print("=" * 40)
    
    # Example 1: Simple data creation and analysis
    print("\nExample 1: Creating and analyzing data")
    print("-" * 40)
    
    # Create some sample data
    create_data_code = """
    data sales;
        input region $ sales;
        datalines;
        North 1000
        South 1500
        East 1200
        West 800
        ;
    run;
    """
    
    result = connect_saspy.submit(create_data_code)
    
    # Analyze the data with PROC MEANS
    analysis_code = """
    proc means data=sales;
        var sales;
    run;
    """
    
    result = connect_saspy.submit(analysis_code)
    
    # Example 2: Generate a report
    print("\nExample 2: Generating a report")
    print("-" * 40)
    
    report_code = """
    proc print data=sales;
        title "Sales Report by Region";
    run;
    
    proc sort data=sales;
        by descending sales;
    run;
    
    proc print data=sales;
        title "Sales Report - Sorted by Sales (Descending)";
    run;
    """
    
    result = connect_saspy.submit(report_code)
    
    # Example 3: Using the class directly for more control
    print("\nExample 3: Using SASConnection class directly")
    print("-" * 40)
    
    # Create a separate connection instance
    my_sas = connect_saspy.SASConnection()
    
    if my_sas.ensure_connection():
        result = my_sas.submit("""
        data summary;
            set sales end=last;
            retain total 0;
            total + sales;
            if last then do;
                avg_sales = total / _n_;
                output;
            end;
            keep total avg_sales;
        run;
        
        proc print data=summary;
            title "Sales Summary Statistics";
        run;
        """)
        
        # Close this specific connection
        my_sas.close()
    
    print("\nExample completed!")
    
    # The global connection will be cleaned up when the script ends
    # But you can explicitly close it if needed:
    # connect_saspy.close_connection()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
        connect_saspy.close_connection()
    except Exception as e:
        print(f"Error occurred: {e}")
        connect_saspy.close_connection()
        raise
