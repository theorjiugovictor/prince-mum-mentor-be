```
Milestones {
  id: string,
  owner_id: string,
  owner_type: string // "mother" | "child"
  name: string, // not-unique
  description: string,
  status: string // pending | completed
  category_id: string, // FK(category, id)
  created_at: datetime,
  updated_at: datetime
}

Categories {
  id: string,
  owner_id: string,
  owner_type: string // "mother" | "child"
  name: string, // not-unique
  description: string,
  created_at: datetime,
  updated_at: datetime
}
```

### **Create Category**

```
POST /milestones/categories
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  body: {
    name: string,
    description: string,
    child_id?: string
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      owner_id: string,
      owner_type: string // "mother" | "child"
      name: string,
      description: string,
      created_at: datetime,
      updated_at: datetime
    }
  }
}
```

### **Update Category**

```
PATCH /milestones/categories/{category_id}
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  params: {
    category_id: string,
  },
  body: {
    name?: string,
    description?: string,
    child_id?: string,
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      owner_id: string,
      owner_type: string // "mother" | "child"
      name: string,
      description: string,
      created_at: datetime,
      updated_at: datetime
    }
  }
}

```

### **List Categories**

```
GET /milestones/categories/
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    child_id?: string,
    cursor?: string,
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      details: [
        {
          id: string,
          owner_id: string,
          owner_type: string // "mother" | "child"
          name: string,
          description: string,
          created_at: datetime,
          updated_at: datetime
          stats: {
            pending_milestones: number,
            completed_milestones: number,
          }
        },
      ],
      pagination: {
        next_cursor: string,
        prev_cursor: string,
        per_page: number,
      }
    }
  }
}
```

### **Delete Category**

```
DELETE /milestones/categories/{category_id}
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    child_id?: string,
  },
  params: {
    category_id: string,
  }
}
Response:
{
  status_code: 204,
  body: {}
}
```

### **Create Milestone**

```
POST /milestones/
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  body: {
    name: string,
    description: string,
    category_id: string
    child_id?: string
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      owner_id: string,
      owner_type: string // "mother" | "child"
      name: string,
      description: string,
      status: string // pending | completed
      category_id: string, 
      created_at: datetime,
      updated_at: datetime
    }
  }
}
```

### **Update Milestone**

```
PATCH /milestones/{milestone_id}
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  params: {
    milestone_id: string,
  },
  body: {
    name?: string,
    description?: string,
    child_id?: string,
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      owner_id: string,
      owner_type: string // "mother" | "child"
      name: string,
      description: string,
      status: string // pending | completed
      category_id: string, 
      created_at: datetime,
      updated_at: datetime
    }
  }
}

```

### **Toggle Milestone Status**

```
PATCH /milestones/{milestone_id}/status
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  body: {
    completed: true,
    child_id?: string
  }
}
Response:
{
  status_code: 201,
  body: {
    message: string,
    success: true,
    data: {
      id: string,
      owner_id: string,
      owner_type: string // "mother" | "child"
      name: string,
      description: string,
      status: string // pending | completed
      category_id: string, 
      created_at: datetime,
      updated_at: datetime
    }
  }
}

```

### **List Milestones**

```
GET /milestones/categories/{category_id}
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  params: {
    category_id: string,
  },
  query: {
    child_id?: string,
    cursor?: string,
    status: string,
  }
}
Response:
{
  status_code: 200,
  body: {
    message: string,
    success: true,
    data: {
      category: {
        id: string,
        owner_id: string,
        owner_type: string // "mother" | "child"
        name: string,
        description: string,
        created_at: datetime,
        updated_at: datetime
        stats: {
          pending_milestones: number,
          completed_milestones: number,
        }
      }
      milestones:[
        {
          id: string,
          owner_id: string,
          owner_type: string // "mother" | "child"
          name: string,
          description: string,
          created_at: datetime,
          updated_at: datetime
        }
      ],
      pagination: {
        next_cursor: string,
        prev_cursor: string,
        per_page: number,
      }
    }
  }
}
```

### **Delete Milestone**

```
DELETE /milestones/{milestone_id}
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    child_id?: string,
  },
  params: {
    milestone_id: string,
  }
}
Response:
{
  status_code: 204,
  body: {}
}
```

### **Get Overall Milestone Progress**

```
GET /milestones/progress
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    child_id?: string,
  }
}
Response:
{
  status_code: 200,
  body: {
    message: string,
    success: true,
    data: {
      pending_milestones: number,
      completed_milestones: number,
    }
  }
}
```

### **Get Milestone Summary**

```
GET /milestones/summary
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    child_id?: string,
    duration?: string // week, month, day, year default: week
  }
}
Response:
{
  status_code: 200,
  body: {
    message: string,
    success: true,
    data: {
      completed_milestones: number,
      created_milestones: number,
    }
  }
}
```

### **Pending Milestones**

```
GET /milestones/pending
Request:
{
  header: { 
    Authorization: "Bearer ..." 
  },
  query: {
    child_id?: string,
  }
}
Response:
{
  status_code: 200,
  body: {
    message: string,
    success: true,
    data: {
      details: [ // sort by ASC - created_at
        {
          id: string,
          owner_id: string,
          owner_type: string // "mother" | "child"
          name: string,
          description: string,
          created_at: datetime,
          updated_at: datetime
        }
      ],
    }
  }
}
```
