# ReimburseAI 🚀

### Smart Expense Reimbursement with Dynamic Approval Workflows

---

## 📌 Overview

ReimburseAI is a smart expense reimbursement platform designed to simplify and automate how companies handle employee expenses.

Traditional reimbursement systems are slow, rigid, and lack transparency. ReimburseAI solves this by introducing a **dynamic rule-based approval engine**, enabling organizations to define flexible workflows tailored to real-world scenarios.

---

## 🎯 Problem Statement

Companies often struggle with:

* Manual and time-consuming reimbursement processes
* Lack of transparency in approvals
* Rigid approval chains that don’t adapt to business needs

---

## 💡 Solution

ReimburseAI provides:

* ⚡ Dynamic approval workflows (sequential, percentage, hybrid)
* 🧠 Smart rule engine for flexible decision-making
* 🌍 Multi-currency expense handling
* 📷 OCR-based receipt scanning (auto data extraction)
* 👥 Role-based access (Admin, Manager, Employee)

---

## 🔥 Key Features

### 👤 Authentication & Roles

* Secure login/signup system
* Role-based access control (Admin, Manager, Employee)

### 💸 Expense Management

* Submit expenses with category, description, and date
* Multi-currency support with real-time conversion
* Track status (Pending, Approved, Rejected)

### 🔄 Smart Approval Engine

* Sequential approval workflows
* Percentage-based approvals (e.g., 60% approval required)
* Specific approver rules (e.g., CFO override)
* Hybrid rules (combination of both)

### 📷 OCR Integration

* Upload receipts
* Automatically extract expense details

### ⚙️ Admin Controls

* Manage users and roles
* Define approval workflows
* Override approvals

---

## 🛠️ Tech Stack

* **Backend:** Flask, SQLAlchemy
* **Frontend:** HTML, Bootstrap
* **Database:** SQLite
* **Authentication:** Flask-Login
* **OCR:** Tesseract (pytesseract)
* **APIs:** Currency conversion & country data

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/reimburseai.git
cd reimburseai
```

### 2️⃣ Install dependencies

```bash
pip install -r requirements.txt
```

### 3️⃣ Run the application

```bash
python app.py
```

### 4️⃣ Open in browser

```
http://127.0.0.1:5000/
```

---

## 🎬 Demo Flow

1. Create a company account (Admin)
2. Add employees and managers
3. Define approval rules
4. Submit an expense (Employee)
5. Approve/reject (Manager/Admin)
6. Watch dynamic workflow execution

---

## 🧠 What Makes It Unique?

Unlike traditional systems, ReimburseAI introduces a **configurable approval engine** that adapts workflows dynamically based on business rules, making it closer to real enterprise solutions.

---

## 🔮 Future Improvements

* Analytics dashboard
* Email/Slack notifications
* Mobile-friendly UI
* AI-based fraud detection

---

## 👨‍💻 Author

Built with ❤️ for hackathons

---

## 📄 License

MIT License
