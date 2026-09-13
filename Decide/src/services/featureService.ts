import { db } from '../firebase';
import {
  doc,
  getDoc,
  setDoc,
  updateDoc,
  increment,
  arrayUnion,
  collection,
  getDocs,
  runTransaction,
  serverTimestamp
} from 'firebase/firestore';

const FEATURE_VOTES_COLLECTION = 'feature_votes';
const USER_GLOBAL_VOTES_COLLECTION = 'user_global_votes';

export interface FeatureVoteData {
  id: string;
  votes: number;
  voterIPs?: string[]; // Store IPs who have voted
}

export interface UserGlobalVoteData {
  votedForFeatureId: string;
  timestamp: any; // Firestore Timestamp
}

// Get vote data for a single feature
export const getFeatureVote = async (featureId: string): Promise<FeatureVoteData | null> => {
  try {
    const docRef = doc(db, FEATURE_VOTES_COLLECTION, featureId);
    const docSnap = await getDoc(docRef);
    if (docSnap.exists()) {
      return { id: docSnap.id, ...docSnap.data() } as FeatureVoteData;
    }
    return null; // Or return a default structure like { id: featureId, votes: 0, voterIPs: [] }
  } catch (error) {
    console.error('Error fetching feature vote:', error);
    throw error;
  }
};

// Get vote data for all features
export const getAllFeatureVotes = async (): Promise<Record<string, FeatureVoteData>> => {
  try {
    const querySnapshot = await getDocs(collection(db, FEATURE_VOTES_COLLECTION));
    const votesMap: Record<string, FeatureVoteData> = {};
    querySnapshot.forEach((docSnap) => {
      if (docSnap.exists()) {
        votesMap[docSnap.id] = { id: docSnap.id, ...docSnap.data() } as FeatureVoteData;
      }
    });
    return votesMap;
  } catch (error) {
    console.error('Error fetching all feature votes:', error);
    throw error;
  }
};

// Get the user's single global vote
export const getUserGlobalVote = async (userIP: string): Promise<UserGlobalVoteData | null> => {
  try {
    const docRef = doc(db, USER_GLOBAL_VOTES_COLLECTION, userIP);
    const docSnap = await getDoc(docRef);
    if (docSnap.exists()) {
      return docSnap.data() as UserGlobalVoteData;
    }
    return null;
  } catch (error) {
    console.error('Error fetching user global vote:', error);
    // Don't throw, allow app to proceed if this lookup fails, UI can adapt
    return null; 
  }
};

// Increment vote for a feature, ensuring one global vote per userIP
export const incrementFeatureVote = async (featureId: string, userIP: string): Promise<{ success: boolean; message: string; newVotes?: number, votedFeatureId?: string }> => {
  const featureVoteDocRef = doc(db, FEATURE_VOTES_COLLECTION, featureId);
  const userGlobalVoteDocRef = doc(db, USER_GLOBAL_VOTES_COLLECTION, userIP);
  let alreadyVotedForFeatureId: string | undefined;

  try {
    let finalNewVotes: number | undefined;

    await runTransaction(db, async (transaction) => {
      // 1. Check if the user has already cast their single global vote
      const userGlobalVoteDoc = await transaction.get(userGlobalVoteDocRef);
      if (userGlobalVoteDoc.exists()) {
        const globalVoteData = userGlobalVoteDoc.data() as UserGlobalVoteData;
        alreadyVotedForFeatureId = globalVoteData?.votedForFeatureId;
        throw new Error(`User has already voted globally for feature: ${alreadyVotedForFeatureId}.`);
      }

      // 2. If not, proceed to vote for the current feature
      const featureDoc = await transaction.get(featureVoteDocRef);
      let currentVotes = 0;

      if (featureDoc.exists()) {
        const data = featureDoc.data() as Omit<FeatureVoteData, 'id'>;
        currentVotes = data.votes || 0;
      }

      // 3. Update feature_votes collection (create or update)
      const newVoteCount = currentVotes + 1;
      if (featureDoc.exists()) {
        transaction.update(featureVoteDocRef, {
          votes: increment(1),
          voterIPs: arrayUnion(userIP) // Keep adding IP to the specific feature's list
        });
      } else {
        transaction.set(featureVoteDocRef, { 
          votes: 1, 
          voterIPs: [userIP] 
        });
      }
      finalNewVotes = newVoteCount;

      // 4. Record the user's global vote in user_global_votes collection
      transaction.set(userGlobalVoteDocRef, { 
        votedForFeatureId: featureId,
        timestamp: serverTimestamp()
      });
    });

    return { 
      success: true, 
      message: 'Vote cast successfully.', 
      newVotes: finalNewVotes, 
      votedFeatureId: featureId 
    };

  } catch (error: any) {
    console.error('Error in transaction for feature vote:', error);
    if (error.message.startsWith('User has already voted globally')) {
      return { success: false, message: error.message, votedFeatureId: alreadyVotedForFeatureId };
    }
    return { success: false, message: 'Failed to cast vote due to a server error.' };
  }
}; 