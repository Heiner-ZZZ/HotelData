import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';
import { HousekeepingApiService } from './housekeeping-api.service';

describe('HousekeepingApiService', () => {
  let service: HousekeepingApiService;
  let httpMock: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [HousekeepingApiService],
    });
    service = TestBed.inject(HousekeepingApiService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should create a housekeeping task with room_id', () => {
    const payload = {
      prop_id: 1,
      room_id: 'HR-1-101',
      task_type: 'cleaning',
      assigned_to: 'María',
      priority: 'high',
      note: 'Test',
      scheduled_date: '2026-07-22',
    };

    service.createTask(payload).subscribe((res) => {
      expect(res.id).toBe('task-1');
      expect(res.roomId).toBe('HR-1-101');
      expect(res.roomLabel).toBe('101');
    });

    const req = httpMock.expectOne(
      (r) => r.url === '/housekeeping/tasks' && r.method === 'POST',
    );
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(payload);
    req.flush({
      id: 'task-1',
      propId: 1,
      roomId: 'HR-1-101',
      roomLabel: '101',
      roomTypeId: 'RT-1-standard',
      roomNumber: '101',
      taskType: 'cleaning',
      status: 'pending',
      assignedTo: 'María',
      priority: 'high',
      note: 'Test',
      scheduledDate: '2026-07-22',
      createdAt: '2026-07-22T00:00:00Z',
      completedAt: null,
    });
  });

  it('should update a housekeeping task with room_id', () => {
    const taskId = 'task-1';
    const payload = {
      prop_id: 1,
      room_id: 'HR-1-102',
      task_type: 'deep_clean',
      assigned_to: 'Pedro',
      priority: 'urgent',
      note: 'Updated',
      scheduled_date: '2026-07-23',
      status: 'pending',
    };

    service.updateTask(taskId, payload).subscribe((res) => {
      expect(res.id).toBe(taskId);
      expect(res.roomId).toBe('HR-1-102');
    });

    const req = httpMock.expectOne(
      (r) => r.url === `/housekeeping/tasks/${taskId}` && r.method === 'PUT',
    );
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual(payload);
    req.flush({
      id: taskId,
      roomId: 'HR-1-102',
      roomLabel: '102',
      taskType: 'deep_clean',
      status: 'pending',
      assignedTo: 'Pedro',
      priority: 'urgent',
      note: 'Updated',
      scheduledDate: '2026-07-23',
      createdAt: '2026-07-22T00:00:00Z',
      completedAt: null,
    });
  });

  it('should complete a housekeeping task', () => {
    const taskId = 'task-1';

    service.completeTask(taskId, 1, 'Done').subscribe((res) => {
      expect(res.id).toBe(taskId);
      expect(res.status).toBe('completed');
    });

    const req = httpMock.expectOne(
      (r) => r.url === `/housekeeping/tasks/${taskId}/complete` && r.method === 'POST',
    );
    expect(req.request.method).toBe('POST');
    expect(req.request.params.get('prop_id')).toBe('1');
    expect(req.request.body).toEqual({ note: 'Done' });
    req.flush({
      id: taskId,
      roomId: 'HR-1-101',
      status: 'completed',
      completedAt: '2026-07-22T12:00:00Z',
    });
  });

  it('should delete a housekeeping task', () => {
    const taskId = 'task-1';

    service.deleteTask(taskId, 1).subscribe((res) => {
      expect(res.id).toBe(taskId);
      expect(res.status).toBe('deleted');
    });

    const req = httpMock.expectOne(
      (r) => r.url === `/housekeeping/tasks/${taskId}` && r.method === 'DELETE',
    );
    expect(req.request.method).toBe('DELETE');
    expect(req.request.params.get('prop_id')).toBe('1');
    req.flush({
      id: taskId,
      status: 'deleted',
    });
  });

  it('should list housekeeping tasks with room_id filter', () => {
    service.getTasks(1, 'pending', 'Maria', 'high', 1).subscribe((res) => {
      expect(res.total).toBe(1);
      expect(res.items[0].roomId).toBe('HR-1-101');
    });

    const req = httpMock.expectOne(
      '/housekeeping/tasks?page=1&prop_id=1&status=pending&assigned_to=Maria&priority=high',
    );
    expect(req.request.method).toBe('GET');
    req.flush({
      items: [
        {
          id: 'task-1',
          propId: 1,
          roomId: 'HR-1-101',
          roomLabel: '101',
          taskType: 'cleaning',
          status: 'pending',
          assignedTo: 'María',
          priority: 'high',
          note: '',
          scheduledDate: '',
          createdAt: '2026-07-22T00:00:00Z',
          completedAt: null,
        },
      ],
      total: 1,
      page: 1,
      pageSize: 20,
      totalPages: 1,
      hasNext: false,
      hasPrev: false,
    });
  });
});
