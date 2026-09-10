<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Student Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        header {
            background-color: #3f51b5;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header-content h1 {
            margin: 0;
            font-size: 24px;
        }
        .header-content p {
            margin: 5px 0 0;
            opacity: 0.9;
        }
        .user-actions {
            display: flex;
            align-items: center;
        }
        .logout-btn {
            background-color: rgba(255,255,255,0.15);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.3s;
            text-decoration: none;
        }
        .logout-btn:hover {
            background-color: rgba(255,255,255,0.25);
        }
        .chart-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }
        .chart-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
            color: #3f51b5;
        }
        canvas {
            width: 100% !important;
            height: 300px !important;
        }
        .student-info {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .student-info h2 {
            margin-top: 0;
            color: #3f51b5;
        }
        .assessment-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }
        .course-assessment {
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        .course-assessment:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }
        .course-title {
            color: #3f51b5;
            font-size: 18px;
            margin-bottom: 10px;
            font-weight: 600;
        }
        .assessment-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        .assessment-item {
            background-color: #f9f9f9;
            padding: 12px;
            border-radius: 6px;
            border-left: 4px solid #3f51b5;
        }
        .assessment-name {
            font-weight: 600;
            margin-bottom: 5px;
        }
        .assessment-score {
            font-size: 16px;
        }
        .score-value {
            font-weight: 600;
            color: #3f51b5;
        }
        .no-data-message {
            text-align: center;
            padding: 40px 20px;
            color: #666;
            font-style: italic;
        }
        .attendance-graphic {
            margin-top: 20px;
        }
        .attendance-card {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .attendance-subject {
            font-weight: 600;
            margin-bottom: 8px;
            color: #3f51b5;
        }
        .attendance-progress {
            height: 20px;
            background-color: #e0e0e0;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 5px;
        }
        .progress-bar {
            height: 100%;
            background-color: #3f51b5;
            border-radius: 10px;
        }
        .attendance-ratio {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
        }
        .attendance-ratio span {
            font-weight: 600;
        }
        @media (max-width: 768px) {
            header {
                flex-direction: column;
                text-align: center;
            }
            .user-actions {
                margin-top: 15px;
            }
            .assessment-list {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-content">
                <h1>Student Performance Dashboard</h1>
                <p>Welcome, {{ current_user.name }} ({{ current_user.user_id }})</p>
            </div>
            <div class="user-actions">
                <a href="{{ url_for('logout') }}" class="logout-btn">Logout</a>
            </div>
        </header>

        <div class="student-info">
            <h2>My Information</h2>
            <p><strong>Name:</strong> {{ current_user.name }}</p>
            <p><strong>Email:</strong> {{ current_user.email }}</p>
            <p><strong>Student ID:</strong> {{ current_user.user_id }}</p>
        </div>
        
        <div class="chart-container attendance-graphic">
            <div class="chart-title">Attendance Details</div>
            {% if attendance_summary and attendance_summary|length > 0 %}
                {% for course in attendance_summary %}
                <div class="attendance-card">
                    <div class="attendance-subject">{{ course.course_name }}</div>
                    <div class="attendance-progress">
                        <div class="progress-bar" style="width: {{ (course.present_count / course.total_classes) * 100 if course.total_classes > 0 else 0 }}%;"></div>
                    </div>
                    <div class="attendance-ratio">
                        <div>Present: <span>{{ course.present_count }}</span></div>
                        <div>Total: <span>{{ course.total_classes }}</span></div>
                        <div>Percentage: <span>{{ ((course.present_count / course.total_classes) * 100) | round(1) if course.total_classes > 0 else 0 }}%</span></div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data-message">No attendance data available</div>
            {% endif %}
        </div>
            
        <div class="assessment-container">
            <div class="chart-title">Assessment Performance</div>
            {% if marks_data and marks_data|length > 0 %}
                {% for course in marks_data %}
                <div class="course-assessment">
                    <div class="course-title">{{ course.course_name }}</div>
                    <div class="assessment-list">
                        {% if course.assessments %}
                            {% for assessment in course.assessments %}
                            <div class="assessment-item">
                                <div class="assessment-name">{{ assessment.name }}</div>
                                <div class="assessment-score">Score: <span class="score-value">{{ assessment.score }}/{{ assessment.max_score }}</span></div>
                            </div>
                            {% endfor %}
                        {% else %}
                            <div class="assessment-item">
                                <div class="assessment-name">IAT1</div>
                                <div class="assessment-score">Score: <span class="score-value">{{ course.iat1_marks|default('N/A') }}</span></div>
                            </div>
                            <div class="assessment-item">
                                <div class="assessment-name">IAT2</div>
                                <div class="assessment-score">Score: <span class="score-value">{{ course.iat2_marks|default('N/A') }}</span></div>
                            </div>
                            <div class="assessment-item">
                                <div class="assessment-name">Assignment 1</div>
                                <div class="assessment-score">Score: <span class="score-value">{{ course.assignment1_marks|default('N/A') }}</span></div>
                            </div>
                            <div class="assessment-item">
                                <div class="assessment-name">Assignment 2</div>
                                <div class="assessment-score">Score: <span class="score-value">{{ course.assignment2_marks|default('N/A') }}</span></div>
                            </div>
                        {% endif %}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data-message">No assessment data available</div>
            {% endif %}
        </div>
    </div>
</body>
</html>