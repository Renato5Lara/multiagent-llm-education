export const queryKeys = {
  auth: {
    all: ['auth'] as const,
    me: () => ['auth', 'me'] as const,
    session: () => ['auth', 'session'] as const,
  },
  users: {
    all: ['users'] as const,
    list: (filters?: Record<string, unknown>) => ['users', 'list', filters] as const,
    detail: (id: string | undefined) => ['users', 'detail', id] as const,
  },
  courses: {
    all: ['courses'] as const,
    list: (filters?: Record<string, unknown>) => ['courses', 'list', filters] as const,
    detail: (id: string | undefined) => ['courses', 'detail', id] as const,
  },
  objectives: {
    all: ['objectives'] as const,
    byCourse: (courseId: string | undefined) => ['objectives', courseId] as const,
  },
  resources: {
    all: ['resources'] as const,
    byCourse: (courseId: string | undefined) => ['resources', courseId] as const,
  },
  competencies: {
    all: ['competencies'] as const,
    list: (type?: string) => ['competencies', type] as const,
    byCourse: (courseId: string | undefined) => ['competencies', 'course', courseId] as const,
  },
  enrollments: {
    all: ['enrollments'] as const,
  },
  student: {
    profile: () => ['student', 'profile'] as const,
    myCourses: () => ['student', 'my-courses'] as const,
    diagnostic: (courseId: string | undefined) => ['student', 'diagnostic', courseId] as const,
    learningPath: (courseId: string | undefined) => ['student', 'learning-path', courseId] as const,
    progress: (courseId: string | undefined) => ['student', 'progress', courseId] as const,
  },
}
