const { ModuleFactory } = require('../../shared/interfaces/moduleInterface');
const TaskService = require('./services/taskService');
const taskRoutes = require('./routes');

/**
 * Tasks Module
 * Handles task management functionality
 * 
 * Phase-2 Implementation:
 * - Migrated from existing services/taskService.js and routes/tasks.js
 * - Uses shared database connection and event bus
 * - Maintains backward compatibility with existing API endpoints
 */
const TasksModule = ModuleFactory.createModule({
  name: 'tasks',
  version: '2.0.0',
  description: 'Task management module for WhatsTask - Phase-2 Implementation',
  
  // Module dependencies
  dependencies: ['database', 'eventBus'],
  
  // Module capabilities
  provides: ['task-management', 'task-notifications', 'task-crud'],
  
  // Module routes
  routes: taskRoutes,
  
  // Module services
  services: {
    taskService: null
  },
  
  /**
   * Initialize the tasks module
   * @param {Object} container - Service container
   * @param {Object} app - Express app instance
   * @param {Object} options - Initialization options
   */
  async initialize(container, app, options = {}) {
    try {
      this.logger = container.get('logger');
      this.logger.info('Initializing Tasks module (Phase-2)...');
      
      // Get dependencies from container
      const database = container.get('database');
      const eventBusRouter = container.get('eventBus');
      
      // Defensive guards for required services
      if (!database) {
        throw new Error('Required service "database" not found in container');
      }
      if (!eventBusRouter) {
        throw new Error('Required service "eventBus" not found in container');
      }
      
      // Initialize task service with shared database connection and event bus router
      this.services.taskService = new TaskService(database, eventBusRouter);
      
      // Register services with container
      container.register('taskService', this.services.taskService, {
        dependencies: ['database', 'eventBus']
      });
      
      // Inject TaskService into app.locals so routes can access it
      app.locals.taskService = this.services.taskService;
      
      // Register routes
      if (this.routes) {
        app.use('/api/tasks', this.routes);
        this.logger.info('Tasks module routes registered at /api/tasks');
      }
      
      // Set up event listeners
      this.setupEventListeners(eventBusRouter);
      
      this.status = 'initialized';
      this.initializedAt = new Date();
      
      this.logger.info('Tasks module initialized successfully (Phase-2)');
      return true;
    } catch (error) {
      this.handleError(error);
      throw error;
    }
  },
  
  /**
   * Set up event listeners for inter-module communication
   * @param {Object} eventBusRouter - Event bus router instance
   */
  setupEventListeners(eventBusRouter) {
    // Listen for task creation events
    eventBusRouter.on('task:created', async (taskData) => {
      try {
        this.logger.info('Task creation event received', { taskId: taskData.id });
        // Handle task creation logic (e.g., notifications, analytics)
        await this.handleTaskCreated(taskData);
      } catch (error) {
        this.logger.error('Error handling task creation event:', error);
      }
    }, { moduleName: 'tasks' });
    
    // Listen for task assignment events
    eventBusRouter.on('task:assigned', async (assignmentData) => {
      try {
        this.logger.info('Task assignment event received', { 
          taskId: assignmentData.taskId,
          assigneeId: assignmentData.assigneeId 
        });
        // Handle task assignment logic
        await this.handleTaskAssigned(assignmentData);
      } catch (error) {
        this.logger.error('Error handling task assignment event:', error);
      }
    }, { moduleName: 'tasks' });
    
    // Listen for task status changes
    eventBusRouter.on('task:status-changed', async (statusData) => {
      try {
        this.logger.info('Task status change event received', {
          taskId: statusData.taskId,
          oldStatus: statusData.oldStatus,
          newStatus: statusData.newStatus
        });
        // Handle task status change logic
        await this.handleTaskStatusChanged(statusData);
      } catch (error) {
        this.logger.error('Error handling task status change event:', error);
      }
    }, { moduleName: 'tasks' });
    
    // Listen for task updates
    eventBusRouter.on('task:updated', async (updateData) => {
      try {
        this.logger.info('Task update event received', {
          taskId: updateData.id,
          updatedFields: Object.keys(updateData.updates)
        });
        // Handle task update logic
        await this.handleTaskUpdated(updateData);
      } catch (error) {
        this.logger.error('Error handling task update event:', error);
      }
    }, { moduleName: 'tasks' });
    
    // Listen for task deletions
    eventBusRouter.on('task:deleted', async (deleteData) => {
      try {
        this.logger.info('Task deletion event received', {
          taskId: deleteData.id,
          deletedAt: deleteData.deletedAt
        });
        // Handle task deletion logic
        await this.handleTaskDeleted(deleteData);
      } catch (error) {
        this.logger.error('Error handling task deletion event:', error);
      }
    }, { moduleName: 'tasks' });
  },
  
  /**
   * Handle task creation events
   * @param {Object} taskData - Task creation data
   */
  async handleTaskCreated(taskData) {
    try {
      // TODO: Implement task creation logic (notifications, analytics, etc.)
      this.logger.info('Task creation handled', { taskId: taskData.id });
    } catch (error) {
      this.logger.error('Error handling task creation:', error);
    }
  },
  
  /**
   * Handle task assignment events
   * @param {Object} assignmentData - Task assignment data
   */
  async handleTaskAssigned(assignmentData) {
    try {
      // TODO: Implement task assignment logic (notifications, etc.)
      this.logger.info('Task assignment handled', { taskId: assignmentData.taskId });
    } catch (error) {
      this.logger.error('Error handling task assignment:', error);
    }
  },
  
  /**
   * Handle task status change events
   * @param {Object} statusData - Task status change data
   */
  async handleTaskStatusChanged(statusData) {
    try {
      // TODO: Implement task status change logic (notifications, etc.)
      this.logger.info('Task status change handled', { taskId: statusData.taskId });
    } catch (error) {
      this.logger.error('Error handling task status change:', error);
    }
  },
  
  /**
   * Handle task update events
   * @param {Object} updateData - Task update data
   */
  async handleTaskUpdated(updateData) {
    try {
      // TODO: Implement task update logic (notifications, etc.)
      this.logger.info('Task update handled', { taskId: updateData.id });
    } catch (error) {
      this.logger.error('Error handling task update:', error);
    }
  },
  
  /**
   * Handle task deletion events
   * @param {Object} deleteData - Task deletion data
   */
  async handleTaskDeleted(deleteData) {
    try {
      // TODO: Implement task deletion logic (cleanup, etc.)
      this.logger.info('Task deletion handled', { taskId: deleteData.id });
    } catch (error) {
      this.logger.error('Error handling task deletion:', error);
    }
  },
  
  /**
   * Health check for the tasks module
   * @returns {Object} Health status
   */
  async health() {
    try {
      const taskServiceHealth = await this.services.taskService.healthCheck();
      
      return {
        status: 'healthy',
        module: 'tasks',
        version: '2.0.0',
        timestamp: new Date().toISOString(),
        services: {
          taskService: taskServiceHealth
        },
        routes: '/api/tasks/*',
        events: ['task:created', 'task:assigned', 'task:status-changed', 'task:updated', 'task:deleted'],
        note: 'Phase-2 implementation - fully functional task management'
      };
    } catch (error) {
      return {
        status: 'error',
        module: 'tasks',
        version: '2.0.0',
        timestamp: new Date().toISOString(),
        error: error.message
      };
    }
  },
  
  /**
   * Start the tasks module
   * @param {Object} container - Service container
   */
  async start(container) {
    try {
      this.logger.info('Starting Tasks module...');
      this.status = 'started';
      this.startedAt = new Date();
      this.logger.info('Tasks module started successfully');
    } catch (error) {
      this.logger.error('Error starting Tasks module:', error);
      throw error;
    }
  },
  
  /**
   * Stop the tasks module
   * @param {Object} container - Service container
   */
  async stop(container) {
    try {
      this.logger.info('Stopping Tasks module...');
      this.status = 'stopped';
      this.stoppedAt = new Date();
      this.logger.info('Tasks module stopped successfully');
    } catch (error) {
      this.logger.error('Error stopping Tasks module:', error);
      throw error;
    }
  },
  
  /**
   * Handle errors in the tasks module
   * @param {Error} error - Error object
   */
  handleError(error) {
    this.logger.error('Tasks module error:', error);
    this.status = 'error';
    this.error = error.message;
  },
  
  /**
   * Reset the tasks module
   */
  reset() {
    this.status = 'registered';
    this.initializedAt = null;
    this.startedAt = null;
    this.stoppedAt = null;
    this.error = null;
  }
});

module.exports = TasksModule;
