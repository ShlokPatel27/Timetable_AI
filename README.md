# 🧬 TimetableAI Scheduler

An AI-powered **university course timetable generator** that uses a **Genetic Algorithm (GA)** to produce optimal, conflict-free schedules. Now professionally restructured for **One-Click Cloud Deployment** on Vercel.

🔗 **[Live Demo: timetableai-seven.vercel.app](https://timetableai-seven.vercel.app/)**

![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JS](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)

---

## ✨ Features

| Feature | Description |
|---|---|
| **Genetic Engine** | Advanced GA with tournament selection, elitism, and automated constraint repair. |
| **Cloud Ready** | Deploy to **Vercel** in seconds with built-in Serverless Functions. |
| **Google Sheets** | Export results directly to a shared spreadsheet for institutional use. |
| **Hard Constraints** | Zero room-time clashes, professor double-booking, or student-group overlaps. |
| **Soft Optimizations** | Lunch window windows, faculty gap minimization, and time preferences. |
| **Modular UI** | Beautiful, dark-themed interface with real-time status pills and charts. |

---

## 🚀 Deployment (Vercel)

The project is now optimized for **Vercel Serverless Functions**.

1.  **Fork/Clone** this repository to your GitHub account.
2.  Go to the [Vercel Dashboard](https://vercel.com/new) and **Import** this project.
3.  **(Optional but Recommended)**: Add your Google Cloud Service Account JSON as an Environment Variable named `GOOGLE_CREDENTIALS_JSON` for secure Google Sheets exports.
4.  **Deploy!** Vercel handles the Python backend (`api/`) and HTML frontend (`public/`) automatically.

---

## 🏗️ Project Structure

```
📦 Time_Table_Ai-project/
├── api/                       # Backend (Vercel Functions)
│   ├── index.py               # GA Runner (/api/run)
│   ├── export_google_sheets.py # Sheets Exporter
│   └── requirements.txt       # Dependencies
├── public/                    # Frontend Assets (Static)
│   ├── index.html             # UI Main Code
│   ├── script.js              # UI Logic
│   └── style.css              # UI Theme
├── timetable_ga.py            # Core GA Engine
├── vercel.json                # Vercel Configuration
├── server_local.py            # Local Dev Server
└── README.md
```

---

## ⚙️ How It Works

### The Genetic Engine
1.  **Initialize**: Randomly generates a population of 100+ candidate schedules.
2.  **Evaluate**: Scores each schedule based on Hard Violations (penalties) and Soft Preferences (bonus).
3.  **Evolve**: Uses **Tournament Selection** and **Single-Point Crossover** to combine the best "genes."
4.  **Repair**: A specialized post-processing step fixes overlapping labs and room segregation errors.
5.  **Converge**: Stops once a conflict-free (Fitness > 0) schedule is found or max generations are reached.

---

## 🔧 Local Development

1.  **Clone & Install**:
    ```bash
    git clone https://github.com/jishnuthacker/Time_Table_Ai-project.git
    cd api/ && pip install -r requirements.txt && cd ..
    ```
2.  **Run Locally**:
    ```bash
    python server_local.py
    ```
3.  **Access**: Open `http://localhost:8080`.

---

## 👥 Authors
- **Jishnu Thacker** - [@jishnuthacker](https://github.com/jishnuthacker)
- **Rikin Parekh** - [@RikinParekh15147](https://github.com/RikinParekh15147)
- **Shlok Patel** - [@ShlokPatel27](https://github.com/ShlokPatel27)

<p align="center">Made with ❤️ and Genetic Algorithm (GA)</p>
