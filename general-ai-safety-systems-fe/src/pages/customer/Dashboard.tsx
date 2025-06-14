import {
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  Avatar,
} from '@mui/material';
import {
  DirectionsBus as BusIcon,
  Person as PersonIcon,
  NotificationsActive as NotificationIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';

const StatusCard = ({ title, status, icon, color }: { title: string; status: string; icon: React.ReactNode; color?: string }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        {icon}
        <Typography variant="h6" component="div" sx={{ ml: 1 }}>
          {title}
        </Typography>
      </Box>
      <Typography variant="body1" color={color || "text.secondary"}>
        {status}
      </Typography>
    </CardContent>
  </Card>
);

export default function CustomerDashboard() {
  const children = [
    {
      id: 1,
      name: 'Emma Johnson',
      grade: '3rd Grade',
      bus: 'Bus #8',
      status: 'On Board',
      time: '8:15 AM',
      avatar: 'E',
    },
    {
      id: 2,
      name: 'Michael Johnson',
      grade: '5th Grade',
      bus: 'Bus #12',
      status: 'Boarding',
      time: '8:30 AM',
      avatar: 'M',
    },
  ];

  const notifications = [
    { id: 1, message: 'Emma has boarded Bus #8', time: '8:15 AM', type: 'success' },
    { id: 2, message: 'Bus #8 is running 5 minutes late', time: '8:10 AM', type: 'warning' },
    { id: 3, message: 'Michael\'s bus is approaching the stop', time: '8:25 AM', type: 'info' },
  ];

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'On Board':
        return <Chip icon={<CheckCircleIcon />} label="On Board" color="success" size="small" />;
      case 'Boarding':
        return <Chip icon={<ScheduleIcon />} label="Boarding" color="info" size="small" />;
      default:
        return <Chip icon={<WarningIcon />} label={status} color="warning" size="small" />;
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        Parent Dashboard
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <StatusCard
            title="Active Notifications"
            status="3 new updates"
            icon={<NotificationIcon color="primary" fontSize="large" />}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <StatusCard
            title="Bus Status"
            status="All buses on schedule"
            icon={<BusIcon color="success" fontSize="large" />}
          />
        </Grid>
        <Grid item xs={12} md={4}>
          <StatusCard
            title="Children Status"
            status="2 children tracked"
            icon={<PersonIcon color="info" fontSize="large" />}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Your Children
            </Typography>
            <List>
              {children.map((child) => (
                <ListItem key={child.id}>
                  <ListItemIcon>
                    <Avatar>{child.avatar}</Avatar>
                  </ListItemIcon>
                  <ListItemText
                    primary={child.name}
                    secondary={`${child.grade} • ${child.bus} • ${child.time}`}
                  />
                  {getStatusChip(child.status)}
                </ListItem>
              ))}
            </List>
            <Button variant="outlined" fullWidth sx={{ mt: 2 }}>
              View Detailed Schedule
            </Button>
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Notifications
            </Typography>
            <List>
              {notifications.map((notification) => (
                <ListItem key={notification.id}>
                  <ListItemIcon>
                    {notification.type === 'success' ? (
                      <CheckCircleIcon color="success" />
                    ) : notification.type === 'warning' ? (
                      <WarningIcon color="warning" />
                    ) : (
                      <NotificationIcon color="info" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={notification.message}
                    secondary={notification.time}
                  />
                </ListItem>
              ))}
            </List>
            <Button variant="outlined" fullWidth sx={{ mt: 2 }}>
              View All Notifications
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
} 