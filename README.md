# systemd2rc
Translate unit files to OpenRC

## Features

*   Description
*   Before
*   After
*   Requires
*   Wants
*   Type (simple, exec, forking and oneshot)
*   ExecStart
*   ExecStop
*   ExecReload
*   PIDFile
*   User
*   Group

For "simple" and "exec" type:

*   WorkingDirectory
*   RootDirectory
*   UMask
*   Nice
*   Environment
*   IOSchedulingClass
*   IOSchedulingPriority
*   StandardOutput=file:...
*   StandardError=file:...

For "oneshot" and "forking" type:

*   WorkingDirectory
*   RootDirectory
*   UMask
*   Nice
*   IOSchedulingClass
*   IOSchedulingPriority
*   CPUSchedulingPolicy
*   CPUSchedulingPriority

### Credits

[OpenRC.run](http://openrc.run/)
