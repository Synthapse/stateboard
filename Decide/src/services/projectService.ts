import { collection, addDoc, query, where, orderBy, getDocs, Timestamp, doc, getDoc, updateDoc, deleteDoc, arrayUnion, arrayRemove } from 'firebase/firestore';
import { db, auth } from '../firebase';

export interface Project {
  id?: string;
  userId: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  reportIds: string[];
}

export interface Task {
  id?: string;
  title: string;
  description: string;
  status: 'todo' | 'in-progress' | 'completed';
  dueDate?: Date;
  assignedTo?: string;
}

export const createProject = async (project: Omit<Project, 'id' | 'createdAt' | 'updatedAt' | 'reportIds'>) => {
  try {
    const user = auth.currentUser;
    if (!user) {
      throw new Error('User not authenticated');
    }

    const projectData = {
      ...project,
      userId: user.uid,
      createdAt: Timestamp.now(),
      updatedAt: Timestamp.now(),
      reportIds: [],
    };

    const docRef = await addDoc(collection(db, 'projects'), projectData);
    return { id: docRef.id, ...projectData };
  } catch (error) {
    console.error('Error creating project:', error);
    throw error;
  }
};

export const getUserProjects = async (): Promise<Project[]> => {
  try {
    const user = auth.currentUser;
    if (!user) {
      throw new Error('User not authenticated');
    }

    const projectsRef = collection(db, 'projects');
    const q = query(
      projectsRef,
      where('userId', '==', user.uid),
      orderBy('createdAt', 'desc')
    );
    
    const querySnapshot = await getDocs(q);
    return querySnapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data(),
      createdAt: (doc.data().createdAt as Timestamp).toDate(),
      updatedAt: (doc.data().updatedAt as Timestamp).toDate(),
    })) as Project[];
  } catch (error) {
    console.error('Error fetching user projects:', error);
    throw error;
  }
};

export const updateProject = async (projectId: string, updates: Partial<Project>) => {
  try {
    const projectRef = doc(db, 'projects', projectId);
    const projectDoc = await getDoc(projectRef);

    if (!projectDoc.exists()) {
      throw new Error('Project not found');
    }

    const projectData = projectDoc.data();
    if (projectData.userId !== auth.currentUser?.uid) {
      throw new Error('Unauthorized to update this project');
    }

    await updateDoc(projectRef, {
      ...updates,
      updatedAt: Timestamp.now(),
    });

    return { id: projectId, ...updates };
  } catch (error) {
    console.error('Error updating project:', error);
    throw error;
  }
};

export const deleteProject = async (projectId: string) => {
  try {
    const projectRef = doc(db, 'projects', projectId);
    const projectDoc = await getDoc(projectRef);

    if (!projectDoc.exists()) {
      throw new Error('Project not found');
    }

    const projectData = projectDoc.data();
    if (projectData.userId !== auth.currentUser?.uid) {
      throw new Error('Unauthorized to delete this project');
    }

    await deleteDoc(projectRef);
    return true;
  } catch (error) {
    console.error('Error deleting project:', error);
    throw error;
  }
};

export const addReportToProject = async (projectId: string, reportId: string) => {
  try {

    console.log(`Adding to project ${projectId} report id |${reportId}`)
    const projectRef = doc(db, 'projects', projectId);
    const projectDoc = await getDoc(projectRef);

    if (!projectDoc.exists()) {
      throw new Error('Project not found');
    }

    const projectData = projectDoc.data();
    if (projectData.userId !== auth.currentUser?.uid) {
      throw new Error('Unauthorized to update this project');
    }

    await updateDoc(projectRef, {
      reportIds: arrayUnion(reportId),
      updatedAt: Timestamp.now(),
    });

    return true;
  } catch (error) {
    console.error('Error adding report to project:', error);
    throw error;
  }
};

export const removeReportFromProject = async (projectId: string, reportId: string) => {
  try {

    console.log(`Remove from project ${projectId} report id |${reportId}`)
    const projectRef = doc(db, 'projects', projectId);
    const projectDoc = await getDoc(projectRef);

    if (!projectDoc.exists()) {
      throw new Error('Project not found');
    }

    const projectData = projectDoc.data();
    if (projectData.userId !== auth.currentUser?.uid) {
      throw new Error('Unauthorized to update this project');
    }

    await updateDoc(projectRef, {
      reportIds: arrayRemove(reportId),
      updatedAt: Timestamp.now(),
    });

    return true;
  } catch (error) {
    console.error('Error removing report from project:', error);
    throw error;
  }
}; 