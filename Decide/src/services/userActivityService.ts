import { collection, addDoc, query, where, orderBy, getDocs, Timestamp } from 'firebase/firestore';
import { db, auth } from '../firebase';

export interface UserActivity {
  id?: string;
  userId: string;
  type: 'marketing-strategy' | 'go-to-market' | 'early-adapters' | 'reddit-audience';
  reportId: string;
  title: string;
  createdAt: Date;
  status: 'completed' | 'pending' | 'failed';
}

export const addUserActivity = async (activity: Omit<UserActivity, 'id' | 'createdAt'>) => {
  try {
    const user = auth.currentUser;
    if (!user) {
      throw new Error('User not authenticated');
    }

    const activityData = {
      ...activity,
      userId: user.uid,
      createdAt: Timestamp.now(),
    };

    const docRef = await addDoc(collection(db, 'userActivities'), activityData);
    return { id: docRef.id, ...activityData };
  } catch (error) {
    console.error('Error adding user activity:', error);
    throw error;
  }
};

export const getUserActivities = async (userId: string | any): Promise<UserActivity[]> => {
  try {

    const activitiesRef = collection(db, 'userActivities');
    const q = query(
      activitiesRef,
      where('userId', '==', userId),
      orderBy('createdAt', 'desc')
    );

    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => {
      const data = doc.data();
      return {
        id: doc.id,
        userId: data.userId,
        type: data.type,
        title: data.title,
        reportId: data.reportId,
        createdAt: (data.createdAt as Timestamp).toDate(),
        status: data.status,
      };
    });
  } catch (error) {
    console.error('Error getting user activities:', error);
    throw error;
  }
}; 