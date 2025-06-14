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
  Chip,
} from '@mui/material';
import type { GridProps } from '@mui/material/Grid';
import {
  DirectionsBus as BusIcon,
  Person as PersonIcon,
  NotificationsActive as NotificationIcon,
  Security as SecurityIcon,
  CheckCircle as CheckCircleIcon,
  Warning as WarningIcon,
} from '@mui/icons-material';

const StatCard = ({ title, value, icon, color }: { title: string; value: string; icon: React.ReactNode; color?: string }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
        {icon}
        <Typography variant="h6" component="div" sx={{ ml: 1 }}>
          {title}
        </Typography>
      </Box>
      <Typography variant="h4" component="div" color={color}>
        {value}
      </Typography>
    </CardContent>
  </Card>
);

export default function AdminDashboard() {
  const stats = [
    {
      title: 'Active Buses',
      value: '12',
      icon: <BusIcon color="primary" fontSize="large" />,
    },
    {
      title: 'Students On Board',
      value: '156',
      icon: <PersonIcon color="success" fontSize="large" />,
    },
    {
      title: 'Pending Notifications',
      value: '8',
      icon: <NotificationIcon color="warning" fontSize="large" />,
    },
    {
      title: 'System Status',
      value: 'All Active',
      icon: <SecurityIcon color="success" fontSize="large" />,
    },
  ];

  const recentActivities = [
    { id: 1, bus: 'Bus #12', student: 'John Smith', status: 'Boarded', time: '8:15 AM' },
    { id: 2, bus: 'Bus #8', student: 'Emma Johnson', status: 'Disembarked', time: '8:20 AM' },
    { id: 3, bus: 'Bus #5', student: 'Michael Brown', status: 'Boarded', time: '8:25 AM' },
  ];

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'Boarded':
        return <Chip icon={<CheckCircleIcon />} label="Boarded" color="success" size="small" />;
      case 'Disembarked':
        return <Chip icon={<CheckCircleIcon />} label="Disembarked" color="info" size="small" />;
      default:
        return <Chip icon={<WarningIcon />} label={status} color="warning" size="small" />;
    }
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4" gutterBottom>
        School Bus Safety Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        {stats.map((stat) => (
          <Grid item xs={12} sm={6} md={3} key={stat.title}>
            <StatCard {...stat} />
          </Grid>
        ))}
      </Grid>

      <Grid container spacing={3} sx={{ mt: 2 }}>
        <Grid xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Recent Student Activities
            </Typography>
            <List>
              {recentActivities.map((activity) => (
                <ListItem key={activity.id}>
                  <ListItemIcon>
                    <PersonIcon />
                  </ListItemIcon>
                  <ListItemText
                    primary={activity.student}
                    secondary={`${activity.bus} • ${activity.time}`}
                  />
                  {getStatusChip(activity.status)}
                </ListItem>
              ))}
            </List>
            <Button variant="outlined" fullWidth sx={{ mt: 2 }}>
              View All Activities
            </Button>
          </Paper>
        </Grid>
        <Grid xs={12} md={6}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>
              Bus Status Overview
            </Typography>
            <List>
              <ListItem>
                <ListItemIcon>
                  <BusIcon color="success" />
                </ListItemIcon>
                <ListItemText
                  primary="Bus #12"
                  secondary="Route: North Campus • 45 students onboard"
                />
                <Chip label="On Route" color="success" size="small" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <BusIcon color="warning" />
                </ListItemIcon>
                <ListItemText
                  primary="Bus #8"
                  secondary="Route: South Campus • 38 students onboard"
                />
                <Chip label="Delayed" color="warning" size="small" />
              </ListItem>
              <ListItem>
                <ListItemIcon>
                  <BusIcon color="info" />
                </ListItemIcon>
                <ListItemText
                  primary="Bus #5"
                  secondary="Route: East Campus • 42 students onboard"
                />
                <Chip label="On Time" color="info" size="small" />
              </ListItem>
            </List>
            <Button variant="outlined" fullWidth sx={{ mt: 2 }}>
              View All Buses
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
} 