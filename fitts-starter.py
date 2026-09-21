import math
import time
import random
from nicegui import ui
import numpy as np

# Textbook defaults used until calibrated
calibrated_a = 0.200  
calibrated_b = 0.100  
is_calibrated = False

trial_state = {
    'start_time': None,
    'current_step': 0, 
    'distance': 300,
    'width': 40
}

# Lists to hold independent (X = Index of Difficulty) and dependent (Y = Actual Time) variables
collected_bits = []
collected_times = []
raw_scatter_points = [] # Holds [distance, time] for plotting

def calculate_fitts(distance, width, use_a, use_b):
    return use_a + use_b * calculate_index_difficulty(distance, width)

def calculate_index_difficulty(distance, width):
    return math.log2(2 * distance / width)

def update_predictor():
    dist = distance_slider.value
    w = width_slider.value
    mt = calculate_fitts(dist, w, calibrated_a, calibrated_b)
    
    prefix = "Calibrated" if is_calibrated else "Predicted"
    result_label.set_text(f"{prefix} Movement Time: {mt:.3f} seconds")

def start_trial():
    trial_state['distance'] = distance_slider.value

    trial_state['width'] = width_slider.value 

    trial_state['current_step'] = 1
    
    left_position = 120 + trial_state['distance']
    
    target_btn.style(f'position: absolute; left: {left_position}px; width: {trial_state["width"]}px; display: block;')
    start_btn.props('disabled')
    trial_state['start_time'] = time.time()

def complete_trial():
    global calibrated_a, calibrated_b, is_calibrated
    if trial_state['current_step'] != 1:
        return
        
    elapsed_time = time.time() - trial_state['start_time']
    actual_dist = trial_state['distance']
    actual_width = trial_state['width']
    
    # Calculate Index of Difficulty (ID) in bits
    idx_difficulty = calculate_index_difficulty(actual_dist, actual_width)
    
    # Save parameters for linear regression to calibrate once 10 trials are complete
    collected_bits.append(idx_difficulty)
    collected_times.append(elapsed_time)
    # Save (dist, time) coordinates to use in the chart 
    raw_scatter_points.append([actual_dist, elapsed_time])
    
    runs_count = len(collected_times)
    
    # Run the linear regression loop once we hit 10 samples
    if runs_count >= 10:
        # np.polyfit(X, Y, 1) returns [slope, intercept] -> [b, a]
        b_slope, a_intercept = np.polyfit(collected_bits, collected_times, 1)
        
        # Prevent math anomalies from bad single clicks (e.g. negative values)
        calibrated_a = max(0.01, a_intercept)
        calibrated_b = max(0.01, b_slope)
        is_calibrated = True

        # Calculate throughput now that a and b are calibrated (in bits per second)
        throughput = 1.0 / calibrated_b
        
        stats_label.set_content(
            f"CALIBRATION COMPLETE!\n"
            f"Your Intercept (a): {calibrated_a:.3f}s | "
            f"Your Slope (b): {calibrated_b:.3f}s/bit | "
            f"Throughput: {throughput:.2f} bits/s"
        )
        stats_label.style('color: #2e7d32; background-color: #e8f5e9; padding: 10px; border-radius: 4px;')
    else:
        stats_label.set_content(f"Logged {runs_count}/10 clicks. Keep doing trials to calibrate...")

    test_result_label.set_text(
        f"Most recent run: {elapsed_time:.3f}s | Model prediction: {calculate_fitts(actual_dist, actual_width, calibrated_a, calibrated_b):.3f}s"
    )
    
    # Refresh chart graphic with latest (distance, time) coordinates including current trial
    chart.options['series'][0]['data'] = raw_scatter_points
    chart.update()
    
    # Reset UI layout
    target_btn.style('display: none;')
    start_btn.props(remove='disabled')
    trial_state['current_step'] = 0

    # Randomize distance slider after each trial.
    distance_slider.set_value(random.randint(distance_slider._props['min'], distance_slider._props['max']))

    width_slider.set_value(random.randint(width_slider._props['min'], width_slider._props['max']))

    update_predictor()

def reset_dataset():
    global calibrated_a, calibrated_b, is_calibrated, collected_bits, collected_times, raw_scatter_points
    calibrated_a = 0.200
    calibrated_b = 0.100
    is_calibrated = False
    collected_bits.clear()
    collected_times.clear()
    raw_scatter_points.clear()
     
    chart.options['series'][0]['data'] = []
    chart.update()
    
    stats_label.set_content("Dataset wiped. Awaiting 10 new taps to recalibrate.")
    stats_label.style('color: #424242; background-color: transparent; padding: 0px;')
    test_result_label.set_text('Waiting for your first run...')
    update_predictor()

# --- UI View Layer ---
ui.markdown("### Fitts's Law Predictions")

ui.markdown("Edited by Tyler Caulfield")

ui.markdown("Change the sliders between clicks to log data across different difficulties.")

with ui.row():
    ui.label("Distance (px)")
    distance_slider = ui.slider(min=50, max=500, value=250, step=10, on_change=update_predictor).props('label-always')
    ui.label("Width (px)")
    width_slider = ui.slider(min=15, max=100, value=40, step=5, on_change=update_predictor).props('label-always')

result_label = ui.label('Predicted Movement Time: ... seconds').style('font-size: 16px; font-weight: bold; color: teal')

ui.markdown("#### Target Trials")

with ui.card().style('width: 100%; height: 120px; background-color: #f8f9fa; position: relative; overflow: hidden;'):
    start_btn = ui.button('Start', on_click=start_trial).props('color=primary').style('position: absolute; left: 20px; width: 100px; top: 38px;')
    target_btn = ui.button('Target', on_click=complete_trial).props('color=negative').style('display: none; top: 38px;')

with ui.row().style('justify-content: space-between; width: 100%; align-items: center;'):
    test_result_label = ui.label('Waiting for your first run...').style('font-size: 14px; font-weight: bold; color: #555;')
    ui.button('Reset System Data', on_click=reset_dataset).props('color=grey-7 outline small')

stats_label = ui.markdown("Awaiting 10 new taps to recalibrate.")

# Visualization Graphic Engine
chart = ui.echart({
    'title': {'text': 'Distance vs. Time for Target Trials'},
    'tooltip': {'trigger': 'item'},
    'xAxis': {'type': 'value', 'name': 'Distance (px)', 'min': 0, 'max': 600},
    'yAxis': {'type': 'value', 'name': 'Time (seconds)', 'min': 0, 'max': 1.5},
    'series': [
        {
            'name': 'Your Clicks',
            'type': 'scatter',
            'data': [],
            'itemStyle': {'color': '#d32f2f'},
            'symbolSize': 12
        }
    ]
})

update_predictor()
ui.run()
